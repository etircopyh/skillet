"""Synthesizer for formatting multi-source research results into high-signal markdown reports."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import config
from .sources.base import SearchResult


class Synthesizer:
    @classmethod
    def format_report(
        cls,
        topic: str,
        results_by_source: Dict[str, List[SearchResult]],
        lookback_days: int = 30,
        deep_readings: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Format the aggregated results into the canonical last30days markdown report."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        badge = f"🌐 last30days v{config.VERSION} · synced {today} · window: {lookback_days} days"

        total_sources = sum(1 for items in results_by_source.values() if items)
        total_items = sum(len(items) for items in results_by_source.values())

        lines = [
            badge,
            "",
            f"# Research Dossier: {topic}",
            f"> Analyzed {total_items} items across {total_sources} platforms over the last {lookback_days} days.",
            "",
        ]

        # 1. Executive Verdict / Key Insights
        lines.append("## 🎯 Ground Truth & Consensus")
        # Synthesize core takeaways based on top items
        top_items = []
        for src, items in results_by_source.items():
            if items:
                top_items.append(items[0])

        if top_items:
            for item in top_items[:4]:
                src_icon = {
                    "x": "🐦",
                    "reddit": "💬",
                    "youtube": "📺",
                    "hackernews": "🔶",
                    "web": "🌐",
                    "github": "🐙",
                    "polymarket": "📊",
                    "arxiv": "📄",
                }.get(item.source, "•")
                summary = item.text[:180].replace("\n", " ").strip() if item.text else item.title
                lines.append(f"- **{src_icon} [{item.title}]({item.url})**: {summary}")
        else:
            lines.append("No definitive signals detected in this time window.")
        lines.append("")

        # 1.5. Wikipedia Momentum Curve
        wiki_items = results_by_source.get("wikipedia", [])
        if wiki_items:
            w = wiki_items[0]
            lines.append(f"## 📈 30-Day Momentum & Interest Curve")
            lines.append(f"[{w.title}]({w.url})\n")
            lines.append(w.text)
            lines.append("")

        # 2. X / Twitter Radar
        x_items = results_by_source.get("x", [])
        if x_items:
            lines.append("## 🐦 X / Twitter Radar")
            for item in x_items[:5]:
                eng = item.engagement
                likes = eng.get("likes", 0)
                rts = eng.get("retweets", 0)
                metrics = []
                if likes:
                    metrics.append(f"❤️ {likes:,}")
                if rts:
                    metrics.append(f"🔄 {rts:,}")
                metric_str = f" · *{', '.join(metrics)}*" if metrics else ""

                quote = item.text.replace("\n", " ").strip()
                lines.append(f"- **[{item.author}]({item.url})**{metric_str}")
                lines.append(f"  > \"{quote}\"")
                lines.append("")

        # 3. Community Voice (Reddit & Hacker News)
        reddit_items = results_by_source.get("reddit", [])
        hn_items = results_by_source.get("hackernews", [])
        if reddit_items or hn_items:
            lines.append("## 💬 Community Consensus & Debates")
            if reddit_items:
                lines.append("### Reddit Discussions")
                for item in reddit_items[:5]:
                    sub = item.metadata.get("subreddit", "")
                    sub_tag = f"`{sub}` " if sub else ""
                    lines.append(f"- {sub_tag}**[{item.title}]({item.url})**")
                    if item.text:
                        lines.append(f"  > {item.text[:220]}...")
                lines.append("")

            if hn_items:
                lines.append("### Hacker News Technical Discourse")
                for item in hn_items[:5]:
                    eng = item.engagement
                    pts = eng.get("points")
                    comm = eng.get("comments")
                    stats = []
                    if pts is not None:
                        stats.append(f"{pts} pts")
                    if comm is not None:
                        stats.append(f"{comm} comments")
                    stat_str = f" (*{', '.join(stats)}*)" if stats else ""

                    if item.metadata.get("type") == "comment":
                        lines.append(f"- **Comment by {item.author}**{stat_str}: [{item.text}]({item.url})")
                    else:
                        lines.append(f"- **[{item.title}]({item.url})**{stat_str}")
                lines.append("")

        # 4. YouTube Deep Dives
        yt_items = results_by_source.get("youtube", [])
        if yt_items:
            lines.append("## 📺 Video Breakdowns & Creator Signals (YouTube)")
            for item in yt_items[:5]:
                eng = item.engagement
                views_str = eng.get("views_display", "")
                pub_str = eng.get("published", "")
                meta_parts = [p for p in [views_str, pub_str] if p]
                meta_str = f" · *{', '.join(meta_parts)}*" if meta_parts else ""

                lines.append(f"- **[{item.title}]({item.url})** by **{item.author}**{meta_str}")
                if item.text:
                    lines.append(f"  {item.text[:180]}...")
            lines.append("")

        # 5. Engineering, Code & Academic Research (GitHub, Dev.to, arXiv)
        gh_items = results_by_source.get("github", [])
        arxiv_items = results_by_source.get("arxiv", [])
        devto_items = results_by_source.get("devto", [])
        if gh_items or arxiv_items or devto_items:
            lines.append("## 🛠️ Code, Tutorials & Research Foundations")
            if gh_items:
                lines.append("### Active GitHub Repositories")
                for item in gh_items[:4]:
                    stars = item.engagement.get("stars", 0)
                    star_str = f"★ {stars:,}" if stars else ""
                    lines.append(f"- **[{item.title}]({item.url})** (*{star_str}*): {item.text[:160]}")
                lines.append("")

            if devto_items:
                lines.append("### Dev.to Guides & Practitioner Takes")
                for item in devto_items[:4]:
                    reactions = item.engagement.get("reactions", 0)
                    react_str = f"♥ {reactions:,}" if reactions else ""
                    lines.append(f"- **[{item.title}]({item.url})** by {item.author} (*{react_str}*): {item.text[:160]}")
                lines.append("")

            if arxiv_items:
                lines.append("### Recent arXiv Preprints")
                for item in arxiv_items[:4]:
                    lines.append(f"- **[{item.title}]({item.url})** ({item.author}):")
                    lines.append(f"  > {item.text[:220]}...")
                lines.append("")

        # 6. Product Launches (Product Hunt)
        ph_items = results_by_source.get("producthunt", [])
        if ph_items:
            lines.append("## 🚀 Product Hunt Launches")
            for item in ph_items[:4]:
                lines.append(f"- **[{item.title}]({item.url})**: {item.text[:200]}")
            lines.append("")

        # 7. Prediction Markets (Polymarket)
        poly_items = results_by_source.get("polymarket", [])
        if poly_items:
            lines.append("## 📊 Prediction Markets (Polymarket)")
            for item in poly_items[:3]:
                lines.append(f"### [{item.title}]({item.url})")
                if item.text:
                    lines.append(item.text)
                lines.append("")

        # 8. Web & News Analysis
        web_items = results_by_source.get("web", [])
        if web_items:
            lines.append("## 🌐 Web & Media Coverage")
            for item in web_items[:5]:
                domain = item.metadata.get("domain", "")
                dom_str = f"`{domain}` " if domain else ""
                lines.append(f"- {dom_str}**[{item.title}]({item.url})**")
                if item.text:
                    lines.append(f"  {item.text[:200]}")
            lines.append("")

        # 8. Deep Readings (Jina Reader)
        if deep_readings:
            lines.append("## 📖 Deep Article Excerpts (via Jina Reader)")
            for r in deep_readings:
                lines.append(f"### [{r.get('title') or r.get('url')}]({r.get('url')})")
                if r.get("published_date"):
                    lines.append(f"*Published: {r.get('published_date')}*")
                content_excerpt = r.get("content", "")[:600].strip()
                lines.append(f"\n{content_excerpt}...\n")

        # 9. Verified Sources Table / Index
        lines.append("---")
        lines.append("### 🔗 Citations & Verified Links")
        citation_count = 0
        for src, items in results_by_source.items():
            for item in items:
                if item.url and item.title:
                    citation_count += 1
                    lines.append(f"{citation_count}. [{item.title}]({item.url}) — *{item.source}*")
                    if citation_count >= 25:
                        break
            if citation_count >= 25:
                break

        return "\n".join(lines)
