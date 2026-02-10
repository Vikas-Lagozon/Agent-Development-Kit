# search_tool.py
from ddgs import DDGS

def search(query: str, max_results: int = 3) -> str:
    """
    Search recent market intelligence and industry reports
    using DuckDuckGo Search (via the official ddgs library).

    Args:
        query: Search query string
               (e.g. "cloud security market growth 2026")
        max_results: Maximum number of top results to return (default: 3)

    Returns:
        Concatenated text snippets from top search results.
        Returns a fallback message if no results are found.
    """
    try:
        with DDGS() as ddgs:
            # Use .text() generator → collects body snippets
            results = [r["body"] for r in ddgs.text(query, max_results=max_results)]

        if not results:
            return "No recent market growth information found."

        # Join with double newlines for readability in LLM context
        return "\n\n".join(results)

    except Exception as e:
        # Graceful fallback so agent doesn't crash
        return f"Search error: {str(e)}. Please try again or use a different query."


if __name__ == "__main__":
    print("=== Search Tool Smoke Test (using ddgs) ===")

    test_queries = [
        "cloud security market growth rate 2026",
        "cloud security CAGR forecast 2025-2030 Gartner OR IDC",
        "cloud security market size 2026"
    ]

    for q in test_queries:
        print(f"\nQuery: {q}")
        print("-" * 60)
        result = search(q)
        print(result)
        print("=" * 80)

