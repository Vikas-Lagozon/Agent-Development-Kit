import os
import faiss
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from pypdf import PdfReader
from docx import Document # pip install python-docx
from sentence_transformers import SentenceTransformer
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# --- CONFIG ---
SOURCE_DIR = "./my_knowledge_base"
DB_PATH = "vector_store.index"
MAP_PATH = "text_map.txt"
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- 1. MULTI-FORMAT FILE EXTRACTORS ---
def extract_text(file_path):
    """Router to handle different file extensions."""
    ext = file_path.suffix.lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(file_path)
            return " ".join([p.extract_text() for p in reader.pages if p.extract_text()])
        elif ext == ".docx":
            doc = Document(file_path)
            return " ".join([p.text for p in doc.paragraphs])
        elif ext in [".txt", ".md", ".csv"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return ""

def load_directory_parallel(directory):
    path = Path(directory)
    files = [f for f in path.glob("**/*") if f.is_file()]
    
    print(f"Found {len(files)} files. Extracting text in parallel...")
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(extract_text, files))
    
    return " ".join(results)

# --- 2. THE RECURSIVE SPLITTER ---
def smart_split(text, chunk_size=1000, overlap=150):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to find a sentence end nearby to avoid cutting mid-sentence
        actual_end = text.find(". ", end - 100, end + 100)
        if actual_end == -1: actual_end = end
        
        chunks.append(text[start:actual_end].strip())
        start = actual_end - overlap
    return [c for c in chunks if len(c) > 50]

# --- 3. VECTOR DB INITIALIZATION ---
def init_rag():
    if os.path.exists(DB_PATH):
        return faiss.read_index(DB_PATH), open(MAP_PATH, "r").read().split("|||")

    raw_text = load_directory_parallel(SOURCE_DIR)
    chunks = smart_split(raw_text)
    
    print(f"Embedding {len(chunks)} chunks...")
    embeddings = embed_model.encode(chunks, show_progress_bar=True)
    
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings).astype('float32'))
    
    faiss.write_index(index, DB_PATH)
    with open(MAP_PATH, "w") as f: f.write("|||".join(chunks))
    return index, chunks

index, all_chunks = init_rag()

# --- 4. ADK TOOL & AGENT ---
def retrieval_tool(query: str) -> str:
    """Searches the entire directory for the most relevant information."""
    query_vec = embed_model.encode([query]).astype('float32')
    # Retrieve top 5 chunks
    _, indices = index.search(query_vec, k=5)
    results = [all_chunks[i] for i in indices[0] if i < len(all_chunks)]
    return "\n---\n".join(results)

knowledge_tool = FunctionTool(retrieval_tool)

agent = Agent(
    name="DirectoryExpert",
    model="gemini-2.0-flash",
    instruction="Search the directory tools to answer questions. Be concise.",
    tools=[knowledge_tool]
)
