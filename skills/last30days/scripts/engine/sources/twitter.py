"""Twitter / X source using search engine dorks + FxTwitter API proxy."""

import concurrent.futures
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class TwitterSource(BaseSource):
    name = "x"
    display_name = "X (Twitter)"
    icon = "🐦"

    def _discover_tweet_ids_via_ddg(self, query: str, limit: int = 15) -> List[str]:
        """Discover tweet IDs matching query via DuckDuckGo Lite search."""
        tweet_ids: List[str] = []
        seen_ids: Set[str] = set()

        search_queries = [
            f"{query} site:x.com",
            f"{query} site:twitter.com",
        ]

        for sq in search_queries:
            data = {"q": sq}
            html = default_client.post_text(config.DDG_LITE_URL, data=data, timeout=8)
            if not html:
                continue

            # Look for tweet URLs in links
            # Matches formats like https://x.com/username/status/123456789...
            matches = re.findall(
                r'https?://(?:www\.)?(?:x|twitter)\.com/[^/\"\'\s]+/status/(\d+)',
                html,
                re.IGNORECASE,
            )
            for tid in matches:
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    tweet_ids.append(tid)
                    if len(tweet_ids) >= limit:
                        return tweet_ids

        return tweet_ids

    def _fetch_tweet_details_fxtwitter(self, tweet_id: str, cutoff_ts: Optional[int] = None) -> Optional[SearchResult]:
        """Fetch rich tweet data from FxTwitter public API."""
        url = f"{config.FXTWITTER_API_BASE}/status/{tweet_id}"
        data = default_client.get_json(url, timeout=6)
        if not data or data.get("code") != 200:
            return None

        tweet = data.get("tweet", {})
        text = tweet.get("text", "").strip()
        if not text:
            return None

        created_at = tweet.get("created_at", "")
        created_ts = tweet.get("created_timestamp")

        # Validate recency cutoff
        if cutoff_ts:
            if created_ts and created_ts < cutoff_ts:
                return None
            if not created_ts and created_at:
                try:
                    # e.g. "Thu Dec 11 16:03:09 +0000 2025"
                    dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                    if dt.timestamp() < cutoff_ts:
                        return None
                except Exception:
                    pass

        author_info = tweet.get("author", {})
        screen_name = author_info.get("screen_name", "")
        name = author_info.get("name", "")
        author_display = f"{name} (@{screen_name})" if screen_name else name

        date_str = ""
        if created_ts:
            try:
                date_str = datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                date_str = created_at
        else:
            date_str = created_at

        likes = tweet.get("likes", 0) or 0
        retweets = tweet.get("retweets", 0) or 0
        replies = tweet.get("replies", 0) or 0
        views = tweet.get("views")

        engagement = {
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
        }
        if views is not None:
            engagement["views"] = views

        return SearchResult(
            title=f"@{screen_name}: {text[:70]}..." if screen_name else text[:70],
            url=tweet.get("url") or f"https://x.com/{screen_name or 'i'}/status/{tweet_id}",
            text=text,
            author=author_display,
            date=date_str,
            source=self.name,
            engagement=engagement,
            metadata={
                "id": tweet_id,
                "likes": likes,
                "retweets": retweets,
            },
        )

    def search(self, query: str, lookback_days: int = 30, limit: int = 15) -> List[SearchResult]:
        """Search Twitter/X by discovering IDs and resolving via FxTwitter proxy."""
        # Query more candidate IDs so that date filtering has enough candidates to satisfy limit
        fetch_limit = max(limit * 2, 20)
        tweet_ids = self._discover_tweet_ids_via_ddg(query, limit=fetch_limit)
        if not tweet_ids:
            return []

        now_ts = int(datetime.now(timezone.utc).timestamp())
        cutoff_ts = now_ts - (lookback_days * 86400)

        results: List[SearchResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_id = {
                executor.submit(self._fetch_tweet_details_fxtwitter, tid, cutoff_ts): tid
                for tid in tweet_ids
            }
            for future in concurrent.futures.as_completed(future_to_id):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception:
                    continue

        # Sort by engagement (likes + retweets)
        results.sort(
            key=lambda x: (x.engagement.get("likes", 0) + x.engagement.get("retweets", 0) * 2),
            reverse=True,
        )
        return results[:limit]

    def probe(self) -> Dict[str, Any]:
        """Verify FxTwitter endpoint with known status ID."""
        start_time = datetime.now(timezone.utc)
        res = self._fetch_tweet_details_fxtwitter("20")  # Jack's first tweet
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if res:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": 1,
                "details": f"FxTwitter proxy active (ping: {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "FxTwitter proxy unreachable",
        }
