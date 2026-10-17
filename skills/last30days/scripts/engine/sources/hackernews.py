"""Hacker News source using Algolia HN Search API."""

import html
import re
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class HackerNewsSource(BaseSource):
    name = "hackernews"
    display_name = "Hacker News"
    icon = "🔶"

    def search(self, query: str, lookback_days: int = 30, limit: int = 15) -> List[SearchResult]:
        """Search Hacker News stories and comments within the lookback window."""
        now_ts = int(time.time())
        cutoff_ts = now_ts - (lookback_days * 86400)
        encoded_query = urllib.parse.quote_plus(query)

        # 1. Fetch top stories
        stories_url = (
            f"{config.HN_ALGOLIA_BASE}/search?"
            f"query={encoded_query}&tags=story&numericFilters=created_at_i>{cutoff_ts}&hitsPerPage={limit}"
        )
        stories_data = default_client.get_json(stories_url, timeout=6) or {}

        # 2. Fetch top comments for community debate quotes
        comments_url = (
            f"{config.HN_ALGOLIA_BASE}/search?"
            f"query={encoded_query}&tags=comment&numericFilters=created_at_i>{cutoff_ts}&hitsPerPage=5"
        )
        comments_data = default_client.get_json(comments_url, timeout=6) or {}

        results: List[SearchResult] = []

        # Process stories
        for hit in stories_data.get("hits", []):
            title = hit.get("title") or ""
            object_id = hit.get("objectID")
            item_url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
            points = hit.get("points") or 0
            num_comments = hit.get("num_comments") or 0
            author = hit.get("author") or ""
            created_at = hit.get("created_at") or ""

            results.append(
                SearchResult(
                    title=title,
                    url=item_url,
                    text=f"Discussion: https://news.ycombinator.com/item?id={object_id}",
                    author=author,
                    date=created_at[:10],
                    source=self.name,
                    engagement={
                        "points": points,
                        "comments": num_comments,
                    },
                    metadata={
                        "hn_id": object_id,
                        "type": "story",
                    },
                )
            )

        # Process top comments as quotes
        for hit in comments_data.get("hits", []):
            raw_text = hit.get("comment_text") or ""
            clean_text = html.unescape(re.sub(r"<[^>]+>", " ", raw_text)).strip()
            clean_text = " ".join(clean_text.split())[:350]
            story_title = hit.get("story_title") or "Discussion"
            object_id = hit.get("objectID")
            author = hit.get("author") or ""
            created_at = hit.get("created_at") or ""

            results.append(
                SearchResult(
                    title=f"Comment on '{story_title}' by {author}",
                    url=f"https://news.ycombinator.com/item?id={object_id}",
                    text=f'"{clean_text}"',
                    author=author,
                    date=created_at[:10],
                    source=self.name,
                    engagement={
                        "points": hit.get("points", 0) or 0,
                    },
                    metadata={
                        "hn_id": object_id,
                        "type": "comment",
                        "story_id": hit.get("story_id"),
                    },
                )
            )

        # Sort stories first by points
        results.sort(key=lambda x: (x.metadata.get("type") == "story", x.engagement.get("points", 0)), reverse=True)
        return results[:limit]

    def probe(self) -> Dict[str, Any]:
        """Probe Algolia HN API."""
        start_time = datetime.now(timezone.utc)
        results = self.search("ai", lookback_days=7, limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"Algolia HN active ({len(results)} items in {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "Algolia HN API failed",
        }
