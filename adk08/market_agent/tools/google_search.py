import requests
from market_agent.config import GOOGLE_API_KEY, GOOGLE_CSE_ID


def google_search(query: str) -> str:
    """
    Search recent market intelligence and industry reports
    using Google Custom Search.

    Args:
        query: Search query string
               (e.g. "cloud security market growth 2026")

    Returns:
        Concise text snippets from top search results.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    items = data.get("items", [])
    if not items:
        return "No recent market growth information found."

    snippets = [
        item.get("snippet", "")
        for item in items[:3]
    ]

    return "\n".join(snippets)

