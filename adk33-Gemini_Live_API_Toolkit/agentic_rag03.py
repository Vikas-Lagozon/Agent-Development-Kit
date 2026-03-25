import os
from typing import List, TypedDict
from pathlib import Path

# 1. LangChain & Data Processing
from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# 2. LangGraph & Orchestration
from langgraph.graph import StateGraph, END

# 3. Google ADK for the "Agent Brains"
from google.adk.agents import Agent

# --- CONFIG ---
DATA_DIR = "./my_massive_library"
DB_PATH = "faiss_index_2026"
# Ensure your GOOGLE_API_KEY is in environment variables
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

# --- STEP 1: PARALLEL DIRECTORY LOADING ---
def get_vector_store():
    if os.path.exists(DB_PATH):
        return FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)

    print("🚀 Ingesting 23,000 pages in parallel...")
    # DirectoryLoader with multithreading enabled for massive speed
    loader = DirectoryLoader(
        DATA_DIR, 
        glob="**/*.*", 
        loader_cls=UnstructuredFileLoader,
        use_multithreading=True,
        max_concurrency=10
    )
    
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    
    vector_db = FAISS.from_documents(chunks, embeddings)
    vector_db.save_local(DB_PATH)
    return vector_db

vector_store = get_vector_store()

# --- STEP 2: DEFINE THE "STATE" ---
class GraphState(TypedDict):
    question: str
    context: List[str]
    answer: str
    retry_count: int
    is_relevant: bool

# --- STEP 3: THE NODES (ADK AGENTS) ---

def retrieval_node(state: GraphState):
    print("🔍 [Node: Researcher] Searching library...")
    query = state["question"]
    docs = vector_store.similarity_search(query, k=5)
    return {"context": [d.page_content for d in docs], "retry_count": state.get("retry_count", 0) + 1}

def grader_node(state: GraphState):
    print("⚖️ [Node: Grader] Evaluating findings...")
    grader_agent = Agent(
        name="Grader",
        model="gemini-2.0-flash",
        instruction="Decide if the context is enough to answer the question. Reply ONLY 'YES' or 'NO'."
    )
    
    prompt = f"Question: {state['question']}\nContext: {state['context']}"
    # ADK returns events; we grab the last text response
    response = list(grader_agent.run(prompt))
    result = response[-1].content.text.strip().upper()
    return {"is_relevant": "YES" in result}

def rewriter_node(state: GraphState):
    print("✍️ [Node: Rewriter] Information missing. Re-phrasing query...")
    rewriter_agent = Agent(
        name="Query_Optimizer",
        model="gemini-2.0-flash",
        instruction="Rewrite the user question to be more technical and specific for a better search."
    )
    
    response = list(rewriter_agent.run(state["question"]))
    return {"question": response[-1].content.text}

def generator_node(state: GraphState):
    print("💎 [Node: Generator] Synthesizing final answer...")
    writer_agent = Agent(
        name="Author",
        model="gemini-2.0-pro", # Use Pro for high-fidelity final output
        instruction="Write a professional report based ONLY on the provided context."
    )
    
    prompt = f"Docs: {state['context']}\nQuestion: {state['question']}"
    response = list(writer_agent.run(prompt))
    return {"answer": response[-1].content.text}

# --- STEP 4: BUILDING THE GRAPH ---

workflow = StateGraph(GraphState)

workflow.add_node("retrieve", retrieval_node)
workflow.add_node("grade", grader_node)
workflow.add_node("rewrite", rewriter_node)
workflow.add_node("generate", generator_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade")

# Conditional Edge: Self-Correction Logic
def route_after_grade(state):
    if state["is_relevant"] or state["retry_count"] >= 3:
        return "generate"
    return "rewrite"

workflow.add_conditional_edges("grade", route_after_grade, {
    "generate": "generate",
    "rewrite": "rewrite"
})

workflow.add_edge("rewrite", "retrieve") # Loop back to try again
workflow.add_edge("generate", END)

app = workflow.compile()

# --- STEP 5: EXECUTION ---
if __name__ == "__main__":
    final_output = app.invoke({"question": "Summarize the automation chapters in the books."})
    print("\n--- FINAL ANSWER ---\n")
    print(final_output["answer"])
