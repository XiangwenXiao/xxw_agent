"""Web search tool using Bing (primary) and DuckDuckGo (fallback). No API key required."""

import asyncio
import re
import urllib.error
import urllib.parse
import urllib.request
from html import unescape

try:
    from ..base import Tool
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from minimal_agent.tools.base import Tool

_CLEAN_RE = re.compile(r"<[^>]+>")


class WebSearchTool(Tool):
    """Perform a web search using DuckDuckGo and return formatted results."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for recent information. Returns titles, snippets, and URLs."

    @property
    def parameters(self) -> dict:
        return {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5, max: 10)",
                "default": 5
            }
        }

    def _search(self, query: str, max_results: int) -> list[dict]:
        """Try search engines in order, return first successful result."""
        engines = [self._search_bing, self._search_duckduckgo]
        for func in engines:
            try:
                results = func(query, max_results)
                if results:
                    return results
            except Exception:
                continue
        return []

    def _fetch(self, url: str) -> str:
        """Fetch URL with browser-like headers, return decoded HTML."""
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _search_bing(self, query: str, max_results: int) -> list[dict]:
        """Search using Bing."""
        encoded = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded}"
        html = self._fetch(url)
        return self._parse_bing(html, max_results)

    def _search_duckduckgo(self, query: str, max_results: int) -> list[dict]:
        """Search using DuckDuckGo Lite."""
        encoded = urllib.parse.quote(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded}"
        html = self._fetch(url)
        return self._parse_duckduckgo(html, max_results)

    def _parse_bing(self, html: str, max_results: int) -> list[dict]:
        """Parse Bing search results HTML."""
        results = []
        # Bing wraps each result in <li class="b_algo">
        block_pattern = re.compile(r'<li[^>]*class="b_algo"[^>]*>(.*?)</li>', re.DOTALL)
        link_pattern = re.compile(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)

        blocks = block_pattern.findall(html)
        for block in blocks:
            if len(results) >= max_results:
                break
            link_match = link_pattern.search(block)
            if not link_match:
                continue
            url = unescape(link_match.group(1))
            title = _CLEAN_RE.sub("", link_match.group(2)).strip()
            title = unescape(title)
            snippet = ""
            snippet_match = snippet_pattern.search(block)
            if snippet_match:
                snippet = _CLEAN_RE.sub("", snippet_match.group(1)).strip()
                snippet = unescape(snippet)
            results.append({"title": title, "url": url, "snippet": snippet})
        return results

    def _parse_duckduckgo(self, html: str, max_results: int) -> list[dict]:
        """Parse DuckDuckGo Lite HTML into structured results."""
        results = []
        link_pattern = re.compile(
            r'<a[^>]*class="result-link"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL
        )
        snippet_pattern = re.compile(
            r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>',
            re.DOTALL
        )

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (href, title) in enumerate(links):
            if i >= max_results:
                break
            title = _CLEAN_RE.sub("", title).strip()
            title = unescape(title)
            snippet = ""
            if i < len(snippets):
                snippet = _CLEAN_RE.sub("", snippets[i]).strip()
                snippet = unescape(snippet)
            results.append({"title": title, "url": href, "snippet": snippet})
        return results

    def _format(self, results: list[dict]) -> str:
        """Format results for display."""
        if not results:
            return "No results found."

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            lines.append(f"   URL: {r['url']}")
            if r["snippet"]:
                lines.append(f"   {r['snippet']}")
            lines.append("")
        return "\n".join(lines)

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        max_results = min(int(kwargs.get("max_results", 5)), 10)

        if not query.strip():
            return "Error: No search query provided"

        try:
            results = await asyncio.to_thread(self._search, query, max_results)
            return self._format(results)
        except urllib.error.URLError as e:
            return f"Error: Network error — {e.reason}"
        except Exception as e:
            return f"Error: Search failed — {str(e)}"


if __name__ == "__main__":
    async def main():
        tool = WebSearchTool()
        print(f"Tool: {tool.name}")
        print(f"Params: {list(tool.parameters.keys())}")
        print()

        query = input("Search query: ").strip()
        if not query:
            query = "Python asyncio tutorial"
            print(f"Using default: {query}")

        print(f"\nSearching...\n")
        result = await tool.execute(query=query, max_results=5)
        print(result)

    asyncio.run(main())
