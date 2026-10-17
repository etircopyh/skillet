"""Web and News search source using Google News RSS, DuckDuckGo Lite, and optional Brave Search."""

import html
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class WebSource(BaseSource):
    name = "web"
    display_name = "Web & News"
    icon = "🌐"

    def _search_google_news_rss(self, query: str, limit: int = 8) -> List[SearchResult]:
        """Fetch real-time breaking news via Google News RSS."""
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        xml_text = default_client.get_text(url, timeout=7)
        if not xml_text:
            return []

        results: List[SearchResult] = []
        try:
            root = ET.fromstring(xml_text)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_elem = item.find("pubDate")
                desc_elem = item.find("description")

                title = title_elem.text if title_elem is not None and title_elem.text else ""
                url_val = link_elem.text if link_elem is not None and link_elem.text else ""
                pub_date = pub_elem.text if pub_elem is not None and pub_elem.text else ""
                desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""

                if not title or not url_val:
                    continue

                clean_desc = html.unescape(re.sub(r"<[^>]+>", " ", desc)).strip()
                clean_desc = " ".join(clean_desc.split())[:250]

                # Extract news publisher from title (often "Title - Publisher")
                publisher = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    publisher = parts[1].strip()

                results.append(
                    SearchResult(
                        title=title,
                        url=url_val,
                        text=clean_desc,
                        author=publisher or "News",
                        date=pub_date[:16] if pub_date else "",
                        source=self.name,
                        engagement={},
                        metadata={"provider": "google_news_rss"},
                    )
                )
                if len(results) >= limit:
                    break
        except Exception:
            pass

        return results

    def _search_ddg_lite(self, query: str, limit: int = 8) -> List[SearchResult]:
        """Fetch organic web search results via DuckDuckGo Lite."""
        data = {"q": query}
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
                if "duckduckgo.com" in link:
                    continue

                raw_title = a_match.group(2)
                clean_title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                snippet = ""
                if td_match:
                    snippet = html.unescape(re.sub(r"<[^>]+>", "", td_match.group(1))).strip()

                domain = urllib.parse.urlparse(link).netloc

                results.append(
                    SearchResult(
                        title=clean_title,
                        url=link,
                        text=snippet,
                        author=domain,
                        date="",
                        source=self.name,
                        engagement={},
                        metadata={"domain": domain, "provider": "ddg_lite"},
                    )
                )
                if len(results) >= limit:
                    break

        return results

    def _search_brave(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Optional enhancement via Brave Search API if BRAVE_API_KEY is configured."""
        if not config.BRAVE_API_KEY:
            return []

        url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count={limit}"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": config.BRAVE_API_KEY,
        }
        data = default_client.get_json(url, headers=headers, timeout=6) or {}
        results: List[SearchResult] = []
        for item in data.get("web", {}).get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    text=item.get("description", ""),
                    author=urllib.parse.urlparse(item.get("url", "")).netloc,
                    date=item.get("page_age", ""),
                    source=self.name,
                    engagement={},
                    metadata={"provider": "brave"},
                )
            )
        return results

    def search(self, query: str, lookback_days: int = 30, limit: int = 15) -> List[SearchResult]:
        """Search Web & News using Google News RSS + DuckDuckGo Lite, augmented by Brave if available."""
        if config.BRAVE_API_KEY:
            brave_res = self._search_brave(query, limit=limit)
            if brave_res:
                return brave_res

        # Pull real-time news via Google News RSS
        news_items = self._search_google_news_rss(query, limit=limit // 2 + 2)
        # Pull organic web results via DDG Lite
        web_items = self._search_ddg_lite(query, limit=limit // 2 + 2)

        seen_urls = set()
        merged = []
        for it in news_items + web_items:
            if it.url not in seen_urls:
                seen_urls.add(it.url)
                merged.append(it)

        return merged[:limit]

    def probe(self) -> Dict[str, Any]:
        """Probe web search capability via Google News RSS."""
        start_time = datetime.now(timezone.utc)
        results = self._search_google_news_rss("technology", limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"Google News RSS active ({len(results)} news items in {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "Web & News search failed",
        }
