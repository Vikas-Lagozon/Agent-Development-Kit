"""
E-Commerce Multi-Agent Demo using Google ADK

This script demonstrates:
1. Session management with ADK
2. A market research agent using Google Search
3. A shopping agent that retrieves items from a vector search backend
"""

# --------------------------------------------------
# Imports
# --------------------------------------------------
import os
import logging
import asyncio
import requests
from typing import List, Dict, Any

from dotenv import load_dotenv, find_dotenv

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.tools import google_search


# --------------------------------------------------
# Environment setup
# --------------------------------------------------
load_dotenv(find_dotenv())

if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# Explicitly disable Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

# Reduce noisy logs
logging.getLogger("google.adk.runners").setLevel(logging.ERROR)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

# --------------------------------------------------
# App / session constants
# --------------------------------------------------
APP_NAME = "ecommerce_agent"
USER_ID = "user_123"
SESSION_ID = "session_123"

# --------------------------------------------------
# Helper: Run an agent once and return final text
# --------------------------------------------------
async def run_agent_once(
    agent: Agent,
    query: str,
    session_service: InMemorySessionService,
) -> str | None:
    """
    Sends a single user query to an agent and returns the final response text.
    """

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content,
    ):
        if event.is_final_response():
            return event.content.parts[0].text if event.content else None

# --------------------------------------------------
# Vector search backend call
# --------------------------------------------------
def call_vector_search(
    url: str,
    query: str,
    rows: int = 3,
) -> Dict[str, Any]:
    """
    Calls a vector search backend and returns the raw JSON response.
    """

    payload = {
        "query": query,
        "rows": rows,
        "dataset_id": "e-commerce-products",
        "use_dense": True,
        "use_sparse": True,
        "rrf_alpha": 0.5,
        "use_rerank": True,
    }

    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()

# --------------------------------------------------
# Tool: Find shopping items
# --------------------------------------------------
def find_shopping_items(
    queries: List[str],
) -> List[Dict[str, Any]]:
    """
    Tool function used by the shopping agent.

    Given a list of search queries, retrieves matching
    items from the e-commerce vector search backend.
    """

    url = "https://www.ac0.cloudadvocacyorg.joonix.net/api/query"
    items: List[Dict[str, Any]] = []

    for query in queries:
        result = call_vector_search(url, query)
        if "items" in result:
            items.extend(result["items"])

    return items

# --------------------------------------------------
# Main application flow
# --------------------------------------------------
async def main():
    """
    Main async entrypoint that:
    1. Creates a session
    2. Runs a research agent
    3. Runs a shopping agent
    """

    # -----------------------------
    # Session setup
    # -----------------------------
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    # -----------------------------
    # Research agent
    # -----------------------------
    research_instruction = """
    You are a market research agent for an e-commerce site.

    When a user provides a shopping intent:
    - Use Google Search to understand what products people commonly buy
    - Generate exactly 5 concise search queries
    - Return ONLY the list of queries
    """

    research_agent = Agent(
        model="gemini-2.0-flash",
        name="research_agent",
        description="Researches shopping trends and generates search queries.",
        instruction=research_instruction,
        tools=[google_search],
    )

    research_response = await run_agent_once(
        research_agent,
        "Birthday present for a 10 year old boy",
        session_service,
    )

    print("\nResearch Agent Output:")
    print(research_response)

    # -----------------------------
    # Shopping agent
    # -----------------------------
    shop_instruction = """
    You are a shopping concierge for an e-commerce site.

    Responsibilities:
    1. Accept a list of product search queries
    2. Use the `find_shopping_items` tool to retrieve products
    3. Present results with name, description, and image URL
    """

    shop_agent = Agent(
        model="gemini-2.0-flash",
        name="shop_agent",
        description="Finds and presents products from the catalog.",
        instruction=shop_instruction,
        tools=[find_shopping_items],
    )

    shop_response = await run_agent_once(
        shop_agent,
        "Find gifts based on these queries:\n" + str(research_response),
        session_service,
    )

    print("\nShop Agent Output:")
    print(shop_response)

# --------------------------------------------------
# Script entrypoint
# --------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
