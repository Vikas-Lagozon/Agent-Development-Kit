import requests
from market_agent.config import GOOGLE_SEARCH_API_KEY, GOOGLE_CSE_ID


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
        "key": GOOGLE_SEARCH_API_KEY,
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


if __name__ == "__main__":
    print("=== Google Search Tool Smoke Test ===")

    result = google_search(
        "cloud security market growth rate 2026"
    )
    print(result)




# (venv) D:\Agent-Development-Kit\adk08>uv run python -m market_agent.tools.google_search
# === Google Search Tool Smoke Test ===
# Traceback (most recent call last):
#   File "<frozen runpy>", line 198, in _run_module_as_main
#   File "<frozen runpy>", line 88, in _run_code
#   File "D:\Agent-Development-Kit\adk08\market_agent\tools\google_search.py", line 44, in <module>
#     result = google_search(
#              ^^^^^^^^^^^^^^
#   File "D:\Agent-Development-Kit\adk08\market_agent\tools\google_search.py", line 25, in google_search
#     response.raise_for_status()
#   File "D:\Agent-Development-Kit\venv\Lib\site-packages\requests\models.py", line 1026, in raise_for_status
#     raise HTTPError(http_error_msg, response=self)
# requests.exceptions.HTTPError: 403 Client Error: Forbidden for url: https://www.googleapis.com/customsearch/v1?key=AIzaSyDJnA30HuiU2DacaTCSCZBLWmhwFlJVNmY&cx=3705eaca13c894a13&q=cloud+security+market+growth+rate+2026
