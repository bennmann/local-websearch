# local-websearch

A local DuckDuckGo web search MCP server. Exposes two tools via the MCP stdio protocol.

The server rate-limits search requests to approximately 30 per minute (2-second minimum interval) to be respectful to DuckDuckGo's infrastructure. Page content fetching is unthrottled but respects standard web etiquette (reasonable User-Agent, 10-second timeout, content truncation to ~6k characters).

## Tools

- **`search(query, max_results)`** — Searches DuckDuckGo and returns titles, URLs, and snippets.
- **`fetch_page_content(url, max_length)`** — Retrieves and cleans the main text content from a URL. Default `max_length` is 15000 characters. (Reference: Wikipedia articles average 10k-20k chars; short articles 3k-5k; long articles 50k+.)

## Installation

```bash
pip install -e .
```

## Vibe Setup

Add to your Vibe configuration:

```toml
[[mcp_servers]]
name = "local-websearch"
transport = "stdio"
command = ["python3", "/path/to/mcp-local-websearch/server.py"]
```

## Generic MCP Client Setup

For any MCP client using stdio transport:

```json
{
  "mcpServers": {
    "local-websearch": {
      "command": "python3",
      "args": ["/path/to/mcp-local-websearch/server.py"]
    }
  }
}
```

## Dependencies

- mcp==1.26.0
- ddgs==9.13.0
- httpx==0.28.1
- beautifulsoup4==4.14.3

## License

Licensed under [Apache 2.0](LICENSE).

Dependencies use permissive licenses (MIT or BSD-3-Clause) compatible with Apache 2.0:

| Dependency | License |
|------------|---------|
| mcp | MIT |
| ddgs | MIT |
| httpx | BSD-3-Clause |
| beautifulsoup4 | MIT |
| lxml (transitive) | BSD-3-Clause |
| primp (transitive) | MIT |
| click (transitive) | BSD-3-Clause |

## AI Usage Disclosure

This project was developed with assistance from AI models: **Mistral Vibe** and **Qwen3 27B** (various Unsloth quants).
