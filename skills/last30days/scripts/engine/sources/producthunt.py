"""Product Hunt source for discovering recent product launches, makers, and taglines."""

import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class ProductHuntSource(BaseSource):
    name = "producthunt"
    display_name = "Product Hunt"
    icon = "🚀"

    def _search_feed(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Check Product Hunt's public launch feed for matching products."""
        url = "https://www.producthunt.com/feed"
        xml_text = default_client.get_text(url, timeout=6)
        if not xml_text:
            return []

        results: List[SearchResult] = []
        q_words = query.lower().split()
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                link_elem = entry.find("atom:link", ns)
                summary_elem = entry.find("atom:summary", ns)
                published_elem = entry.find("atom:published", ns)

                title = title_elem.text if title_elem is not None and title_elem.text else ""
                url_val = link_elem.attrib.get("href") if link_elem is not None else ""
                summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""
                published = published_elem.text if published_elem is not None and published_elem.text else ""

                if not title or not url_val:
                    continue

                clean_summary = html.unescape(re.sub(r"<[^>]+>", " ", summary)).strip()
                clean_summary = " ".join(clean_summary.split())

                combined = f"{title.lower()} {clean_summary.lower()}"
                if any(w in combined for w in q_words):
                    results.append(
                        SearchResult(
                            title=f"Launch: {title}",
                            url=url_val,
                            text=clean_summary[:250],
                            author="Product Hunt",
                            date=published[:10],
                            source=self.name,
                            engagement={},
                            metadata={"type": "product_launch"},
                        )
                    )
                    if len(results) >= limit:
                        break
        except Exception:
            pass

        return results

    def _search_ddg(self, query: str, limit: int = 5) -> List[SearchResult]:
        """Search Product Hunt launch posts via DDG Lite."""
        data = {"q": f"{query} site:producthunt.com/posts/"}
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
                if "producthunt.com/posts/" in link:
                    title_raw = a_match.group(2)
                    clean_title = html.unescape(re.sub(r"<[^>]+>", "", title_raw)).strip()
                    snippet = ""
                    if td_match:
                        snippet = html.unescape(re.sub(r"<[^>]+>", "", td_match.group(1))).strip()

                    results.append(
                        SearchResult(
                            title=f"Product: {clean_title}",
                            url=link,
                            text=snippet[:250],
                            author="Product Hunt",
                            date="",
                            source=self.name,
                            engagement={},
                            metadata={"type": "product_post"},
                        )
                    )
                    if len(results) >= limit:
                        break

        return results

    def search(self, query: str, lookback_days: int = 30, limit: int = 6) -> List[SearchResult]:
        """Search Product Hunt via launch feed and search dorks."""
        results = self._search_feed(query, limit=limit)
        if len(results) < limit:
            dork_results = self._search_ddg(query, limit=limit - len(results))
            seen = {r.url for r in results}
            for d in dork_results:
                if d.url not in seen:
                    results.append(d)
        return results[:limit]

    def probe(self) -> Dict[str, Any]:
        """Probe Product Hunt launch feed."""
        start_time = datetime.now(timezone.utc)
        url = "https://www.producthunt.com/feed"
        text = default_client.get_text(url, timeout=5)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if text and "<entry>" in text:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": 1,
                "details": f"Product Hunt launch feed active (ping: {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "Product Hunt feed unreachable",
        }
