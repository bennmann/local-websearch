# (issue draft) for https://github.com/bennmann/local-websearch

---

**Title:** `fetch_page_content` silently corrupts JSON responses; README's "web etiquette" claims don't match the code

Filed from real usage: I used this server as a `jq`-free reader for the GitHub REST API (the host had no
`jq`, so "fetch a URL and give me text" was the obvious tool). It returned JSON that looked fine and parsed
fine — by luck, because that particular payload contained no `<` and no double spaces. The pipeline in
`fetch_page_content` is not safe for anything that isn't HTML, and the failure is silent.

Reproducible offline against the shipped code — no network needed:

```python
# the exact pipeline from server.py:77-89
def pipeline(raw):
    soup = BeautifulSoup(raw, "html.parser")
    for el in soup(["script", "style", "header", "footer", "nav", "aside"]):
        el.decompose()
    text = soup.get_text(separator="\n")
    lines = (l.strip() for l in text.splitlines())
    chunks = (p.strip() for l in lines for p in l.split("  "))
    return "\n".join(c for c in chunks if c)
```

| input | output | result |
|---|---|---|
| `{"body":"fix  done"}` | `{"body":"fix\ndone"}` | invalid JSON (raw newline inside a string literal) |
| `{"title":"use <linux/mman.h> here"}` | `{"title":"use\nhere"}` | `<linux/mman.h>` **deleted** by `get_text()` |
| `{"note":"call <script> then madvise"}` | `{"note":"call"` | `<script>` swallows the rest of the document |

`get_text()` treats `<anything>` as a tag and drops the tag text, so *any* payload with angle brackets loses
content; the `split("  ")` whitespace pass then injects newlines inside string values. For llama.cpp PR
bodies and diffs — full of `<...>` and aligned double spaces — this is data loss with no error and no warning.

## 1. Gate the HTML extraction on content-type (bug, high)

`server.py:77` parses every response as HTML regardless of what it is. Minimal fix, right after
`response.raise_for_status()`:

```python
            ctype = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
            if ctype not in ("text/html", "application/xhtml+xml"):
                # JSON / XML / YAML / text: the body *is* the content. Parsing it as HTML
                # deletes <...> tokens, and the whitespace pass breaks JSON string literals.
                return response.text[:max_length]
```

Worth deciding deliberately: either this tool is an *HTML reader* (then non-HTML should be an explicit
error), or it is a general URL fetcher (then non-HTML must be returned verbatim). Silently HTML-parsing
JSON is the one combination that produces wrong answers.

## 2. The User-Agent is a browser impersonation, not a "reasonable" one (etiquette, medium)

`server.py:69` sends `Mozilla/5.0 (Windows NT 10.0; ... ) Chrome/122.0.0.0 Safari/537.36`. Consequences:

- Hosts cannot identify the client, contact the operator, or apply a policy — the whole point of a UA.
- A stale hardcoded Chrome version is a worse fingerprint than an honest one: it *claims* to be a browser
  and matches no real browser build, which is exactly the signal bot walls look for.
- API hosts ask for something else entirely (GitHub's API guidelines want an identifying UA with a contact).

Suggestion: identify the tool, keep the browser string opt-in.

```python
USER_AGENT = os.environ.get(
    "WEBSEARCH_USER_AGENT",
    "local-websearch/0.1 (+https://github.com/bennmann/local-websearch)",
)
```

If the Chrome UA is there because DDG needs it for `search`, that argues for *per-tool* UAs (`search` uses
the browser string, `fetch_page_content` uses the honest one), not one global spoof.

## 3. `fetch_page_content` is unthrottled (etiquette, medium)

`search` has a 2 s minimum interval (`server.py:13,25-29`); `fetch_page_content` has nothing, and the README
is honest about that ("unthrottled"). The gap matters because a caller that loops over URLs — polling an API,
walking a search result set — gets no protection at all, and unlike DDG the target is a third party who never
agreed to the rate. Suggested: a small per-host minimum interval (reuse the existing lock pattern), plus
honour `Retry-After` on 429/503 instead of letting `raise_for_status()` throw the body away.

Related: nothing consults `robots.txt`. For one manual fetch that is pedantic; for a loop it is the
difference between scraping and hammering. At minimum a README note that the tool does not check it.

## 4. Errors are returned *as if they were page content* (correctness, medium)

`server.py:97-98` returns `f"Error fetching page content: {str(e)}"`. A caller — especially a model — cannot
distinguish "the page says this" from "the request failed", and a 404 page's text can look like an answer.
`search` (`server.py:53-55`) has the same shape. Suggest raising an MCP error (or at least a hard marker like
`[FETCH FAILED: 404]`) and never letting a failure string masquerade as document text.

## 5. README vs code (docs)

- README intro: "content truncation to **~6k characters**". The default is **15000** (`server.py:57`), and the
  README's own Tools section says 15000. One of the two is stale.
- README intro: fetching "respects standard web etiquette (**reasonable User-Agent**, ...)". As of `073d5b5`
  the UA is a Chrome impersonation (see 2), so this sentence is doing the opposite of its intent.

## 6. Test gap

`test_mcp.py` only exercises `search` (`def test_search`). Every bug above is in the untested tool. Three
table-driven cases would have caught the corruption: a JSON body with a double space, a payload containing
`<linux/mman.h>`, and one containing `<script>`. These need no network — feed the pipeline directly.

## 7. Nit

`server.py:25,29` use `asyncio.get_event_loop()`, deprecated since 3.10 in a running loop; use
`asyncio.get_running_loop().time()`.
