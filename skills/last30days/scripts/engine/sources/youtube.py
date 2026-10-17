"""YouTube source using native ytInitialData extraction (zero binary dependencies)."""

import json
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..http_client import default_client
from .base import BaseSource, SearchResult


def _is_within_lookback(published_text: str, lookback_days: int) -> bool:
    """Validate whether relative published text is within the lookback window."""
    if not published_text:
        return True
    text = published_text.lower().strip()
    m = re.search(r"(\d+)\s*(second|sec|minute|min|hour|hr|day|d|week|w|month|mo|year|yr|y)", text)
    if not m:
        return True

    val = int(m.group(1))
    unit = m.group(2)
    if unit in ("second", "sec", "minute", "min", "hour", "hr"):
        days = 0
    elif unit in ("day", "d"):
        days = val
    elif unit in ("week", "w"):
        days = val * 7
    elif unit in ("month", "mo"):
        days = val * 30
    elif unit in ("year", "yr", "y"):
        days = val * 365
    else:
        days = 0

    # Allow a slight 3-day grace margin for fuzzy "1 month ago" (e.g. 33 days)
    return days <= (lookback_days + 3)


class YouTubeSource(BaseSource):
    name = "youtube"
    display_name = "YouTube"
    icon = "📺"

    def search(self, query: str, lookback_days: int = 30, limit: int = 15) -> List[SearchResult]:
        """Fetch YouTube videos by querying search and extracting embedded ytInitialData JSON."""
        encoded_query = urllib.parse.quote(query)

        # YouTube upload date filter 'sp' protobuf tokens:
        # EgIIAg%253D%253D = Today
        # EgIIAw%253D%253D = This week
        # EgIIBA%253D%253D = This month
        # EgIIBQ%253D%253D = This year
        sp_param = ""
        if lookback_days <= 1:
            sp_param = "&sp=EgIIAg%253D%253D"
        elif lookback_days <= 7:
            sp_param = "&sp=EgIIAw%253D%253D"
        elif lookback_days <= 30:
            sp_param = "&sp=EgIIBA%253D%253D"
        elif lookback_days <= 365:
            sp_param = "&sp=EgIIBQ%253D%253D"

        # Search URL with sp filter
        url = f"https://www.youtube.com/results?search_query={encoded_query}{sp_param}"
        headers = {
            "Accept-Language": "en-US,en;q=0.9",
        }
        html_text = default_client.get_text(url, headers=headers, timeout=10)
        if not html_text:
            return []

        # Find ytInitialData JSON object
        m = re.search(r"ytInitialData\s*=\s*({.+?});</script>", html_text)
        if not m:
            m = re.search(r"var ytInitialData\s*=\s*({.+?});", html_text)
        if not m:
            return []

        results: List[SearchResult] = []
        try:
            data = json.loads(m.group(1))
            sections = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            for sec in sections:
                item_section = sec.get("itemSectionRenderer", {}).get("contents", [])
                for item in item_section:
                    vr = item.get("videoRenderer")
                    if not vr:
                        continue

                    vid_id = vr.get("videoId")
                    if not vid_id:
                        continue

                    title_runs = vr.get("title", {}).get("runs", [])
                    title = title_runs[0].get("text", "") if title_runs else ""
                    if not title:
                        continue

                    channel_runs = vr.get("ownerText", {}).get("runs", [])
                    channel = channel_runs[0].get("text", "") if channel_runs else ""

                    views_text = vr.get("viewCountText", {}).get("simpleText", "")
                    published_text = vr.get("publishedTimeText", {}).get("simpleText", "")

                    # Filter out videos outside the lookback window
                    if not _is_within_lookback(published_text, lookback_days):
                        continue

                    desc_runs = (
                        vr.get("detailedMetadataSnippets", [{}])[0]
                        .get("snippetText", {})
                        .get("runs", [])
                    )
                    snippet = "".join([r.get("text", "") for r in desc_runs]) if desc_runs else ""

                    # Engagement parsing
                    views_count = 0
                    if views_text:
                        digits = re.sub(r"[^\d]", "", views_text)
                        if digits:
                            views_count = int(digits)

                    results.append(
                        SearchResult(
                            title=title,
                            url=f"https://www.youtube.com/watch?v={vid_id}",
                            text=snippet,
                            author=channel,
                            date=published_text,
                            source=self.name,
                            engagement={
                                "views": views_count,
                                "views_display": views_text,
                                "published": published_text,
                            },
                            metadata={
                                "video_id": vid_id,
                                "channel": channel,
                            },
                        )
                    )
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
        except Exception:
            pass

        return results

    def probe(self) -> Dict[str, Any]:
        """Probe YouTube search."""
        start_time = datetime.now(timezone.utc)
        results = self.search("technology news", limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"YouTube parser active ({len(results)} videos in {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "YouTube search failed or blocked",
        }
