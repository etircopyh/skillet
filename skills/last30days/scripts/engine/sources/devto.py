"""Dev.to source for developer tutorials, engineering blogs, and practitioner reactions."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import urllib.parse

from ..http_client import default_client
from .base import BaseSource, SearchResult


class DevToSource(BaseSource):
    name = "devto"
    display_name = "Dev.to Articles"
    icon = "✍️"

    def search(self, query: str, lookback_days: int = 30, limit: int = 10) -> List[SearchResult]:
        """Search Dev.to articles via public REST API with recency enforcement."""
        encoded_query = urllib.parse.quote(query)
        fetch_limit = max(limit * 2, 25)
        url = f"https://dev.to/api/articles?q={encoded_query}&per_page={fetch_limit}"

        data = default_client.get_json(url, timeout=6) or []
        if not isinstance(data, list):
            return []

        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        results: List[SearchResult] = []
        for item in data:
            title = item.get("title") or ""
            article_url = item.get("url") or ""
            desc = item.get("description") or ""
            author_obj = item.get("user") or {}
            author_name = author_obj.get("name") or author_obj.get("username") or ""
            reactions = item.get("positive_reactions_count") or 0
            comments = item.get("comments_count") or 0
            published_at = item.get("published_at") or ""
            tag_list = item.get("tag_list") or []

            # Verify published date within lookback window
            if published_at:
                try:
                    pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                    if pub_dt < cutoff_dt:
                        continue
                except Exception:
                    pass

            tags_str = f"[{', '.join(tag_list[:3])}] " if tag_list else ""

            results.append(
                SearchResult(
                    title=f"{tags_str}{title}",
                    url=article_url,
                    text=desc,
                    author=author_name,
                    date=published_at[:10],
                    source=self.name,
                    engagement={
                        "reactions": reactions,
                        "comments": comments,
                    },
                    metadata={
                        "tags": tag_list,
                        "reading_time_minutes": item.get("reading_time_minutes"),
                    },
                )
            )

        # Sort by reaction engagement
        results.sort(key=lambda x: x.engagement.get("reactions", 0), reverse=True)
        return results[:limit]

    def probe(self) -> Dict[str, Any]:
        """Probe Dev.to API."""
        start_time = datetime.now(timezone.utc)
        results = self.search("python", limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"Dev.to API active ({len(results)} articles in {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "Dev.to API failed",
        }
