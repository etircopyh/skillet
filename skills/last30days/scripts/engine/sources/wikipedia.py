"""Wikipedia Momentum Source: tracks 30-day pageview velocity and interest curves."""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import urllib.parse

from ..http_client import default_client
from .base import BaseSource, SearchResult


def generate_sparkline(numbers: List[int]) -> str:
    """Generate an ASCII sparkline representation of a numerical series."""
    if not numbers:
        return ""
    ticks = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    min_v = min(numbers)
    max_v = max(numbers)
    if min_v == max_v:
        return ticks[0] * len(numbers)
    step = (max_v - min_v) / (len(ticks) - 1)
    return "".join(ticks[min(len(ticks) - 1, int((n - min_v) / step))] for n in numbers)


class WikipediaSource(BaseSource):
    name = "wikipedia"
    display_name = "Wikipedia Momentum"
    icon = "📈"

    def search(self, query: str, lookback_days: int = 30, limit: int = 1) -> List[SearchResult]:
        """Resolve topic to Wikipedia article and calculate 30-day view velocity."""
        # 1. Resolve Wikipedia title using OpenSearch
        opensearch_url = (
            f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}"
            "&limit=1&namespace=0&format=json"
        )
        search_data = default_client.get_json(opensearch_url, timeout=5)
        if not search_data or len(search_data) < 4 or not search_data[1]:
            return []

        article_title = search_data[1][0]
        article_url = search_data[3][0]
        snippet = search_data[2][0] if len(search_data) > 2 and search_data[2] else ""
        slug = article_title.replace(" ", "_")

        # 2. Query Wikimedia Pageviews API for lookback window
        end_dt = date.today() - timedelta(days=1)
        start_dt = end_dt - timedelta(days=lookback_days)
        start_str = start_dt.strftime("%Y%m%d")
        end_str = end_dt.strftime("%Y%m%d")

        pv_url = (
            f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/all-agents/"
            f"{urllib.parse.quote(slug)}/daily/{start_str}/{end_str}"
        )
        pv_data = default_client.get_json(pv_url, timeout=6) or {}
        items = pv_data.get("items", [])
        if not items:
            return []

        daily_views = [it.get("views", 0) for it in items]
        total_views = sum(daily_views)
        avg_daily = total_views // len(daily_views) if daily_views else 0
        max_views = max(daily_views) if daily_views else 0
        peak_idx = daily_views.index(max_views) if daily_views else 0
        peak_timestamp = items[peak_idx].get("timestamp", "")[:8]
        peak_date_str = f"{peak_timestamp[:4]}-{peak_timestamp[4:6]}-{peak_timestamp[6:8]}" if len(peak_timestamp) == 8 else ""

        # Calculate momentum trajectory: compare last 7 days vs first 7 days
        recent_avg = sum(daily_views[-7:]) / 7.0 if len(daily_views) >= 7 else avg_daily
        past_avg = sum(daily_views[:7]) / 7.0 if len(daily_views) >= 7 else avg_daily
        if past_avg > 0:
            trend_pct = round(((recent_avg - past_avg) / past_avg) * 100, 1)
        else:
            trend_pct = 0.0

        trend_direction = "Rising ↗" if trend_pct > 15 else "Falling ↘" if trend_pct < -15 else "Steady →"
        sparkline = generate_sparkline(daily_views)

        summary_text = (
            f"• 30-Day Total Pageviews: {total_views:,} (avg {avg_daily:,}/day)\n"
            f"• Momentum Trend: {trend_direction} ({trend_pct:+}%) | Curve: [{sparkline}]\n"
            f"• Peak Day: {peak_date_str} with {max_views:,} views"
        )
        if snippet:
            summary_text = f"{snippet}\n\n{summary_text}"

        return [
            SearchResult(
                title=f"Wikipedia Momentum: {article_title}",
                url=article_url,
                text=summary_text,
                author="Wikipedia",
                date=peak_date_str,
                source=self.name,
                engagement={
                    "total_pageviews": total_views,
                    "avg_daily_pageviews": avg_daily,
                    "peak_views": max_views,
                    "trend_pct": trend_pct,
                    "trend_direction": trend_direction,
                },
                metadata={
                    "article_title": article_title,
                    "sparkline": sparkline,
                    "daily_views": daily_views,
                },
            )
        ]

    def probe(self) -> Dict[str, Any]:
        """Probe Wikimedia Pageviews API."""
        start_time = datetime.now(timezone.utc)
        results = self.search("Python (programming language)", limit=1)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": 1,
                "details": f"Pageviews API active (ping: {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "Wikimedia API failed",
        }
