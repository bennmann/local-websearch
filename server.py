import asyncio
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from ddgs import DDGS
import httpx
from bs4 import BeautifulSoup

# Initialize FastMCP server
mcp = FastMCP("websearch")

@mcp.tool()
async def search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo (via ddgs).
    Returns titles, URLs, and snippets.
    """
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
async def fetch_page_content(url: str) -> str:
    """
    Retrieves the main text content from a specific URL.
    Use this to read the details of a specific search result.
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
            
            # Truncate to avoid blowing out LLM context windows (approx 6k chars)
            limit = 6000
            if len(clean_text) > limit:
                return clean_text[:limit] + "\n\n... [Content truncated for brevity] ..."
            
            return clean_text

    except Exception as e:
        return f"Error fetching page content: {str(e)}"

if __name__ == "__main__":
    mcp.run()
