import asyncio
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from ddgs import DDGS
import httpx
from bs4 import BeautifulSoup

# Initialize FastMCP server
mcp = FastMCP("websearch")

# Rate limiting: prevent overwhelming DuckDuckGo
_search_lock = asyncio.Lock()
_MIN_SEARCH_INTERVAL = 2.0  # seconds between search requests
_last_search_time = 0.0

@mcp.tool()
async def search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo (via ddgs).
    Returns titles, URLs, and snippets.
    Rate-limited to ~30 requests per minute to be respectful to DuckDuckGo.
    """
    global _last_search_time
    async with _search_lock:
        now = asyncio.get_event_loop().time()
        wait_time = _MIN_SEARCH_INTERVAL - (now - _last_search_time)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        _last_search_time = asyncio.get_event_loop().time()

    try:
        # DDGS is a synchronous context manager
        with DDGS() as ddgs:
            # Fetch results
            results = ddgs.text(query, max_results=max_results)

        if not results:
            return f"No results found for: {query}"

        formatted_results = []
        for i, res in enumerate(results, 1):
            # ddgs returns dicts with 'title', 'href', and 'body'
            title = res.get("title", "No Title")
            url = res.get("href", "No URL")
            body = res.get("body", "No description available.")
            
            formatted_results.append(
                f"{i}. {title}\n   URL: {url}\n   Snippet: {body}"
            )

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Search error: {str(e)}"

@mcp.tool()
async def fetch_page_content(url: str, max_length: int = 15000) -> str:
    """
    Retrieves the main text content from a specific URL.
    Use this to read the details of a specific search result.

    Args:
        url: The URL to fetch.
        max_length: Maximum characters to return (default 15000).
            Reference: Wikipedia articles average 10k-20k chars.
            Short articles: 3k-5k. Long articles: 50k+.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove "noise" elements
            for element in soup(["script", "style", "header", "footer", "nav", "aside"]):
                element.decompose()

            # Extract text
            text = soup.get_text(separator='\n')

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)

            # Truncate to avoid blowing out LLM context windows
            if len(clean_text) > max_length:
                return clean_text[:max_length] + "\n\n... [Content truncated for brevity] ..."

            return clean_text

    except Exception as e:
        return f"Error fetching page content: {str(e)}"

def print_help():
    print("local-websearch — A local DuckDuckGo web search MCP server.")
    print()
    print("Usage:")
    print("  python3 server.py              Run as MCP stdio server (default)")
    print("  python3 server.py --help       Show this help message")
    print()
    print("Tools:")
    print("  search(query, max_results)     Search DuckDuckGo. Default max_results=5.")
    print("  fetch_page_content(url, max_length)  Fetch page text. Default max_length=15000.")
    print()
    print("Rate limiting: ~30 searches/min (2s minimum interval).")
    print()
    print("License: Apache 2.0")
    print()
    print("AI Usage Disclosure:")
    print("  This project was developed with assistance from AI models:")
    print("  Mistral Vibe and Qwen3 27B (various Unsloth quants).")

if __name__ == "__main__":
    import sys
    if "--help" in sys.argv:
        print_help()
        sys.exit(0)
    mcp.run()
