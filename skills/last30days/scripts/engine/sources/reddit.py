"""Reddit source using RSS feeds, DDG search dorks, and Arctic Shift fallbacks."""

import html
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
import xml.etree.ElementTree as ET

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class RedditSource(BaseSource):
    name = "reddit"
    display_name = "Reddit"
    icon = "💬"

    # Common high-signal subreddits for tech, business, and general discussions
    DEFAULT_TECH_SUBS = ["technology", "programming", "artificial", "MachineLearning", "LocalLLaMA", "ChatGPT"]

    def _search_rss(self, query: str, subreddit: Optional[str] = None, limit: int = 15) -> List[SearchResult]:
        """Fetch posts via Reddit's Atom/RSS feeds."""
        encoded_query = urllib.parse.quote_plus(query)
        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search.rss?q={encoded_query}&restrict_sr=1&sort=relevance&t=month"
        else:
            url = f"https://www.reddit.com/search.rss?q={encoded_query}&sort=relevance&t=month"

        xml_text = default_client.get_text(url, timeout=8)
        if not xml_text:
            return []

        results: List[SearchResult] = []
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)
            for entry in entries:
                title_elem = entry.find("atom:title", ns)
                link_elem = entry.find("atom:link", ns)
                updated_elem = entry.find("atom:updated", ns)
                author_elem = entry.find("atom:author/atom:name", ns)
                content_elem = entry.find("atom:content", ns)

                title = title_elem.text if title_elem is not None and title_elem.text else ""
                url_val = link_elem.attrib.get("href") if link_elem is not None else ""
                date_val = updated_elem.text if updated_elem is not None and updated_elem.text else ""
                author_val = author_elem.text if author_elem is not None and author_elem.text else ""

                if not url_val or not title:
                    continue

                # Ignore top-level subreddit links (e.g. https://www.reddit.com/r/technology/)
                if "/comments/" not in url_val:
                    continue

                # Strip HTML from content snippet
                snippet = ""
                if content_elem is not None and content_elem.text:
                    clean = re.sub(r"<[^>]+>", " ", content_elem.text)
                    snippet = html.unescape(clean).strip()
                    # Collapse multiple spaces
                    snippet = " ".join(snippet.split())[:300]

                # Extract subreddit name from url
                sub_match = re.search(r"/r/([^/]+)/", url_val)
                sub_name = sub_match.group(1) if sub_match else ""

                results.append(
                    SearchResult(
                        title=title,
                        url=url_val,
                        text=snippet,
                        author=f"u/{author_val}" if author_val else "",
                        date=date_val[:10] if date_val else "",
                        source=self.name,
                        engagement={"score": 0, "num_comments": 0},
                        metadata={"subreddit": f"r/{sub_name}" if sub_name else ""},
                    )
                )
                if len(results) >= limit:
                    break
        except Exception:
            pass

        return results

    def _search_ddg_dork(self, query: str, limit: int = 15) -> List[SearchResult]:
        """Discover Reddit threads via DDG Lite search."""
        dork_query = f"{query} site:reddit.com/r/"
        data = {"q": dork_query}
        html_text = default_client.post_text(config.DDG_LITE_URL, data=data, timeout=8)
        if not html_text:
            return []

        results: List[SearchResult] = []
        rows = re.findall(r"<tr>(.*?)</tr>", html_text, re.DOTALL)
        for r in rows:
            a_match = re.search(r'<a\b[^>]*href=[\'\"](https?://[^\'\"]+)[\'\"][^>]*>(.*?)</a>', r, re.DOTALL)
            td_match = re.search(r'<td[^>]*class=[\'\"]result-snippet[\'\"][^>]*>(.*?)</td>', r, re.DOTALL)
            if a_match:
                link = a_match.group(1)
                if "reddit.com/r/" in link and "/comments/" in link:
                    raw_title = a_match.group(2)
                    clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                    snippet = ""
                    if td_match:
                        snippet = html.unescape(re.sub(r"<[^>]+>", "", td_match.group(1))).strip()

                    sub_match = re.search(r"/r/([^/]+)/", link)
                    sub_name = sub_match.group(1) if sub_match else ""

                    results.append(
                        SearchResult(
                            title=clean_title,
                            url=link,
                            text=snippet,
                            author="",
                            date="",
                            source=self.name,
                            engagement={"score": 0, "num_comments": 0},
                            metadata={"subreddit": f"r/{sub_name}" if sub_name else ""},
                        )
                    )
                    if len(results) >= limit:
                        break

        return results

    def search(self, query: str, lookback_days: int = 30, limit: int = 15, subreddits: Optional[List[str]] = None) -> List[SearchResult]:
        """Search Reddit via RSS, falling back to DDG search dork."""
        seen_urls: Set[str] = set()
        merged: List[SearchResult] = []

        # If specific subreddits are requested, search them directly
        if subreddits:
            for sub in subreddits:
                sub_results = self._search_rss(query, subreddit=sub, limit=5)
                for r in sub_results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        merged.append(r)

        # Global RSS search
        if len(merged) < limit:
            rss_results = self._search_rss(query, limit=limit)
            for r in rss_results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    merged.append(r)

        # Supplement with DDG dorking if fewer than requested
        if len(merged) < limit:
            dork_results = self._search_ddg_dork(query, limit=limit)
            for r in dork_results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    merged.append(r)

        return merged[:limit]

    def probe(self) -> Dict[str, Any]:
        """Probe Reddit search capability."""
        start_time = datetime.now(timezone.utc)
        results = self._search_ddg_dork("technology", limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"Reddit discovery active ({len(results)} items in {round(duration_ms)}ms)",
            }
        return {
            "status": "DEGRADED",
            "latency_ms": round(duration_ms, 1),
            "count": 0,
            "details": "Direct Reddit blocked; proxy fallback active",
        }
