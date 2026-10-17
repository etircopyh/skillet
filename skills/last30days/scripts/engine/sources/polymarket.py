"""Polymarket source for prediction markets and real-world consensus odds."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
import urllib.parse

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class PolymarketSource(BaseSource):
    name = "polymarket"
    display_name = "Polymarket"
    icon = "📊"

    def search(self, query: str, lookback_days: int = 30, limit: int = 10) -> List[SearchResult]:
        """Search prediction markets on Polymarket via Gamma public search."""
        encoded_query = urllib.parse.quote_plus(query)
        url = f"{config.POLYMARKET_GAMMA_BASE}/public-search?q={encoded_query}"

        data = default_client.get_json(url, timeout=6) or {}
        events = data.get("events", [])

        results: List[SearchResult] = []
        for ev in events:
            title = ev.get("title") or ""
            slug = ev.get("slug") or ""
            event_url = f"https://polymarket.com/event/{slug}" if slug else ""
            desc = ev.get("description") or ""

            # Extract market questions and odds
            markets = ev.get("markets", [])
            odds_summaries = []
            for m in markets[:3]:
                question = m.get("question") or title
                outcomes = m.get("outcomes", [])
                prices = m.get("outcomePrices", [])

                if isinstance(outcomes, str):
                    try:
                        outcomes = json.loads(outcomes)
                    except Exception:
                        outcomes = []
                if isinstance(prices, str):
                    try:
                        prices = json.loads(prices)
                    except Exception:
                        prices = []

                if outcomes and prices and len(outcomes) == len(prices):
                    odds_pairs = []
                    for outcome_label, price_str in zip(outcomes, prices):
                        try:
                            prob = round(float(price_str) * 100, 1)
                            odds_pairs.append(f"{outcome_label}: {prob}%")
                        except Exception:
                            continue
                    if odds_pairs:
                        odds_summaries.append(f"• {question} -> {', '.join(odds_pairs)}")

            market_text = "\n".join(odds_summaries) if odds_summaries else desc

            results.append(
                SearchResult(
                    title=f"Market: {title}",
                    url=event_url,
                    text=market_text,
                    author="Polymarket",
                    date="",
                    source=self.name,
                    engagement={"markets_count": len(markets)},
                    metadata={"slug": slug, "markets": markets[:2]},
                )
            )
            if len(results) >= limit:
                break

        return results

    def probe(self) -> Dict[str, Any]:
        """Probe Polymarket Gamma public search API."""
        start_time = datetime.now(timezone.utc)
        results = self.search("AI", limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"Polymarket active ({len(results)} markets in {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "Polymarket Gamma API failed",
        }
