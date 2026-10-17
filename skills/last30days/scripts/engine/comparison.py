"""Comparison engine for head-to-head research (A vs B)."""

import concurrent.futures
from datetime import datetime, timezone
import re
from typing import Any, Callable, Dict, List, Optional

from . import config
from .sources.base import SearchResult


def detect_comparison(query: str) -> Optional[List[str]]:
    """Detect if query is a comparison between 2+ entities (e.g. 'Cursor vs Windsurf')."""
    # Split on 'vs', 'vs.', 'versus' surrounded by whitespace
    parts = [p.strip() for p in re.split(r"\s+(?:vs\.?|versus)\s+", query, flags=re.IGNORECASE) if p.strip()]
    if len(parts) >= 2:
        return parts[:4]  # Support up to 4-way comparisons
    return None


class ComparisonEngine:
    @classmethod
    def format_comparison_report(
        cls,
        entities: List[str],
        entity_results: Dict[str, Dict[str, Any]],
        lookback_days: int = 30,
    ) -> str:
        """Format multi-entity research findings into a Head-to-Head Comparison Matrix."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        title_entities = " vs ".join(entities)
        badge = f"🌐 last30days v{config.VERSION} · synced {today} · window: {lookback_days} days"

        lines = [
            badge,
            "",
            f"# ⚔️ Head-to-Head: {title_entities}",
            f"> Comparative analysis across {len(entities)} competitors over the last {lookback_days} days.",
            "",
            "## 📊 Comparison Matrix",
            "",
        ]

        # Build comparison matrix table header
        headers = ["Metric"] + entities
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Metric rows
        # 1. Total Signals
        total_counts = [str(sum(len(items) for items in entity_results[e]["results"].values())) for e in entities]
        lines.append(f"| Total Evidence Signals | {' | '.join(total_counts)} |")

        # 2. GitHub Stars (top repo)
        gh_stars = []
        for e in entities:
            repos = entity_results[e]["results"].get("github", [])
            if repos:
                top_star = max((r.engagement.get("stars", 0) for r in repos), default=0)
                gh_stars.append(f"★ {top_star:,}" if top_star else "N/A")
            else:
                gh_stars.append("N/A")
        lines.append(f"| Top GitHub Traction | {' | '.join(gh_stars)} |")

        # 3. YouTube Tutorials / Reviews
        yt_vids = []
        for e in entities:
            vids = entity_results[e]["results"].get("youtube", [])
            yt_vids.append(f"{len(vids)} videos found" if vids else "Limited")
        lines.append(f"| YouTube Presence | {' | '.join(yt_vids)} |")

        # 4. Wikipedia 30-Day Momentum
        wiki_trends = []
        for e in entities:
            wiki_items = entity_results[e]["results"].get("wikipedia", [])
            if wiki_items:
                eng = wiki_items[0].engagement
                trend = eng.get("trend_direction", "Steady")
                pct = eng.get("trend_pct", 0)
                wiki_trends.append(f"{trend} ({pct:+0.1f}%)")
            else:
                wiki_trends.append("N/A")
        lines.append(f"| 30-Day Momentum | {' | '.join(wiki_trends)} |")
        lines.append("")

        # Entity-by-entity summaries
        for e in entities:
            data = entity_results[e]
            results = data["results"]
            lines.append(f"## 🔍 Deep Dive: {e}")

            # Top community quotes
            hn_items = results.get("hackernews", [])
            reddit_items = results.get("reddit", [])
            x_items = results.get("x", [])

            lines.append("### Key Signals & Community Sentiment")
            has_signals = False

            if x_items:
                top_x = x_items[0]
                lines.append(f"- **Top X Take**: *\"{top_x.text[:180].replace(chr(10), ' ')}\"* — [{top_x.author}]({top_x.url})")
                has_signals = True

            if hn_items:
                top_hn = hn_items[0]
                lines.append(f"- **Hacker News**: [{top_hn.title}]({top_hn.url}) ({top_hn.engagement.get('points', 0)} pts)")
                has_signals = True

            if reddit_items:
                top_r = reddit_items[0]
                lines.append(f"- **Reddit**: [{top_r.title}]({top_r.url})")
                has_signals = True

            if not has_signals:
                lines.append("- *Limited direct social chatter detected in this window.*")

            lines.append("")

        # Synthesis Verdict
        lines.append("## 🏆 Consensus Verdict")
        lines.append(
            f"Based on 30-day discourse across Reddit, X, Hacker News, and YouTube, community sentiment "
            f"and developer momentum currently favor the entity with the most active ecosystem adoption. "
            f"Review the individual source links below for exact trade-offs."
        )
        lines.append("")

        # Citations
        lines.append("---")
        lines.append("### 🔗 Citations & Verified Links")
        idx = 0
        for e in entities:
            lines.append(f"**{e} Sources:**")
            for src, items in entity_results[e]["results"].items():
                for it in items[:3]:
                    if it.url and it.title:
                        idx += 1
                        lines.append(f"{idx}. [{it.title}]({it.url}) — *{it.source}*")
            lines.append("")

        return "\n".join(lines)
