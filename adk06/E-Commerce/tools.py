"""
Reusable tools for the e-commerce agents.

This file contains ONLY pure functions or ADK tools.
No sessions, no agents, no async code.
"""

import requests
from typing import List, Dict, Any


def call_vector_search(
    url: str,
    query: str,
    rows: int = 3,
) -> Dict[str, Any]:
    """
    Call the vector search backend.

    Args:
        url: Vector search API endpoint
        query: Search query text
        rows: Number of results to return

    Returns:
        Raw JSON response from the backend
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


def find_shopping_items(
    queries: List[str],
) -> List[Dict[str, Any]]:
    """
    ADK tool: Retrieve shopping items for a list of queries.

    Args:
        queries: List of search queries

    Returns:
        Flattened list of product items
    """

    url = "https://www.ac0.cloudadvocacyorg.joonix.net/api/query"
    items: List[Dict[str, Any]] = []

    for query in queries:
        result = call_vector_search(url, query)
        if "items" in result:
            items.extend(result["items"])

    return items
