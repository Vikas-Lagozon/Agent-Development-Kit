import os
import faiss
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer
from google.adk.agents import Agent
from google.adk.tools import tool

# --- CONFIGURATION ---
DATA_DIR = "./my_books"  # Put your 3 huge books here
DB_PATH = "rag_index.index"
MAP_PATH = "rag_map.txt"
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- SECTION 1: HIGH-SPEED DIRECTORY LOADING ---
def extract_text(file_path):
    path = Path(file_path)
    ext = path.suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            r = PdfReader(path); text = " ".join([p.extract_text() for p in r.pages if p.extract_text()])
        elif ext == ".docx":
            d = Document(path); text = " ".join([p.text for p in d.paragraphs])
        elif ext in [".txt", ".md"]:
            with open(path, "r", encoding="utf-8") as f: text = f.read()
    except Exception as e: print(f"Error {file_path}: {e}")
    return text

def init_vector_db():
    if os.path.exists(DB_PATH):
        return faiss.read_index(DB_PATH), open(MAP_PATH, "r", encoding="utf-8").read().split("|||")

    # Multiprocessing: Read 23k pages across all CPU cores
    files = list(Path(DATA_DIR).glob("**/*.*"))
    with ProcessPoolExecutor() as executor:
        texts = list(executor.map(extract_text, files))
    
    # Recursive Chunking logic (Pure Python)
    full_text = " ".join(texts)
    chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 850)] # 150 char overlap
    
    print(f"Indexing {len(chunks)} chunks. This is a one-time process...")
    embeddings = embed_model.encode(chunks, show_progress_bar=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings).astype('float32'))
    
    faiss.write_index(index, DB_PATH)
    with open(MAP_PATH, "w", encoding="utf-8") as f: f.write("|||".join(chunks))
    return index, chunks

index, all_chunks = init_vector_db()

# --- SECTION 2: SPECIALIZED TOOLS ---
@tool
def fetch_book_data(query: str) -> str:
    """Retrieves specific technical facts from the 23,000-page library."""
    query_vec = embed_model.encode([query]).astype('float32')
    _, indices = index.search(query_vec, k=5)
    results = [all_chunks[i] for i in indices[0] if i < len(all_chunks)]
    return "\n---\n".join(results)

# --- SECTION 3: MULTI-AGENT ORCHESTRATION ---

# 1. The Researcher (Worker)
researcher = Agent(
    name="Researcher",
    model="gemini-2.0-flash", # Fast & focused
    instruction="Extract raw facts from the library using fetch_book_data. No opinions.",
    tools=[fetch_book_data]
)

# 2. The Manager (Orchestrator)
manager = Agent(
    name="Manager",
    model="gemini-2.0-pro", # Higher reasoning for management
    instruction="""
    You are the Lead Analyst for a 23,000-page project.
    1. Break user queries into 3 targeted search terms.
    2. Delegate those terms to the Researcher.
    3. If the Researcher finds conflicting info, ask for a deeper search.
    4. Summarize the final findings into a structured report for the user.
    """,
    sub_agents=[researcher]
)

# --- SECTION 4: EXECUTION ---
if __name__ == "__main__":
    query = "What are the common themes between the three books regarding automation?"
    print(f"Querying Multi-Agent System...\n")
    
    for event in manager.run(query):
        # The ADK streams events as agents talk to each other
        if event.content:
            # We filter to see the interaction
            prefix = f"[{event.agent_name}]"
            print(f"{prefix}: {event.content.text[:500]}...")

