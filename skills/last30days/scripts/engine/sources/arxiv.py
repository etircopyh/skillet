"""arXiv source for recent preprints and research papers."""

from datetime import datetime, timezone
from typing import Any, Dict, List
import urllib.parse
import xml.etree.ElementTree as ET

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class ArxivSource(BaseSource):
    name = "arxiv"
    display_name = "arXiv Papers"
    icon = "📄"

    def search(self, query: str, lookback_days: int = 30, limit: int = 10) -> List[SearchResult]:
        """Search arXiv for recent preprints."""
        encoded_query = urllib.parse.quote_plus(f"all:{query}")
        url = (
            f"{config.ARXIV_API_BASE}?search_query={encoded_query}"
            f"&sortBy=submittedDate&sortOrder=descending&max_results={limit}"
        )

        xml_text = default_client.get_text(url, timeout=10)
        if not xml_text:
            return []

        results: List[SearchResult] = []
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)
            for entry in entries:
                title_elem = entry.find("atom:title", ns)
                id_elem = entry.find("atom:id", ns)
                summary_elem = entry.find("atom:summary", ns)
                published_elem = entry.find("atom:published", ns)
                author_elems = entry.findall("atom:author/atom:name", ns)

                title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else ""
                url_val = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                summary = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None and summary_elem.text else ""
                published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
                authors = [a.text.strip() for a in author_elems if a.text]
                author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")

                # Clean whitespace in summary
                summary = " ".join(summary.split())[:350]

                if not title or not url_val:
                    continue

                results.append(
                    SearchResult(
                        title=title,
                        url=url_val,
                        text=summary,
                        author=author_str,
                        date=published[:10],
                        source=self.name,
                        engagement={"authors_count": len(authors)},
                        metadata={"authors": authors},
                    )
                )
        except Exception:
            pass

        return results

    def probe(self) -> Dict[str, Any]:
        """Probe arXiv API."""
        start_time = datetime.now(timezone.utc)
        results = self.search("transformer", limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"arXiv export API active ({len(results)} papers in {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "arXiv API failed",
        }
