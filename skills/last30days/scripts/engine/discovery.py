"""Discovery engine: sweeps river feeds to surface top breakout topics across the last 30 days."""

import concurrent.futures
from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Optional
import urllib.parse

from . import config
from .http_client import default_client


class DiscoveryEngine:
    @classmethod
    def discover_trends(cls, category: str = "ai", lookback_days: int = 30) -> str:
        """Sweep Hacker News, GitHub, and Product Hunt for breakout topics."""
        now_ts = int(time.time())
        cutoff_ts = now_ts - (lookback_days * 86400)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

        hn_results: List[Dict[str, Any]] = []
        gh_results: List[Dict[str, Any]] = []
        ph_results: List[Dict[str, Any]] = []

        def fetch_hn():
            nonlocal hn_results
            encoded_cat = urllib.parse.quote_plus(category if category != "all" else "")
            query_param = f"query={encoded_cat}&" if encoded_cat else ""
            url = (
                f"{config.HN_ALGOLIA_BASE}/search?{query_param}tags=story&"
                f"numericFilters=created_at_i>{cutoff_ts},points>120&hitsPerPage=10"
            )
            data = default_client.get_json(url, timeout=6) or {}
            hn_results = data.get("hits", [])

        def fetch_gh():
            nonlocal gh_results
            cat_query = category if category != "all" else "developer"
            url = (
                f"{config.GITHUB_API_BASE}/search/repositories?"
                f"q={urllib.parse.quote(cat_query)}+pushed:>{cutoff_date}&sort=stars&order=desc&per_page=8"
            )
            headers = {"Accept": "application/vnd.github.v3+json"}
            if config.GITHUB_TOKEN:
                headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
            data = default_client.get_json(url, headers=headers, timeout=6) or {}
            gh_results = data.get("items", [])

        def fetch_ph():
            nonlocal ph_results
            url = "https://www.producthunt.com/feed"
            xml_text = default_client.get_text(url, timeout=6)
            if xml_text:
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(xml_text)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns)[:5]:
                        t = entry.find("atom:title", ns)
                        l = entry.find("atom:link", ns)
                        if t is not None and l is not None:
                            ph_results.append({
                                "title": t.text or "",
                                "url": l.attrib.get("href") or "",
                            })
                except Exception:
                    pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(fetch_hn), executor.submit(fetch_gh), executor.submit(fetch_ph)]
            for f in concurrent.futures.as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass

        # Synthesize top breakout trends
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        badge = f"🌐 last30days v{config.VERSION} · synced {today} · window: {lookback_days} days"

        lines = [
            badge,
            "",
            f"# 🔥 Trend Radar & Breakout Discovery: [{category.upper()}]",
            f"> Autonomous sweep of top breakout stories, viral repos, and launches over the last {lookback_days} days.",
            "",
            "## ⚡ Top Breakout Topics",
            "",
        ]

        rank = 1
        # 1. Top HN Viral Discussions
        for h in hn_results[:3]:
            title = h.get("title") or ""
            points = h.get("points") or 0
            comments = h.get("num_comments") or 0
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"

            lines.append(f"### {rank}. 🔥 {title}")
            lines.append(f"- **Momentum**: `{points:,} points` · `{comments:,} comments` on Hacker News")
            lines.append(f"- **Primary Link**: [{title}]({url})")
            lines.append(f"- **Deep Dive Command**: `last30days \"{title[:50]}\"`")
            lines.append("")
            rank += 1

        # 2. Top GitHub Viral Repos
        for r in gh_results[:3]:
            name = r.get("full_name") or ""
            stars = r.get("stargazers_count") or 0
            desc = r.get("description") or "No description provided."
            url = r.get("html_url") or ""
            lang = r.get("language") or "Code"

            lines.append(f"### {rank}. 🚀 {name} ({lang})")
            lines.append(f"- **Momentum**: `★ {stars:,} stars` (active commits this month)")
            lines.append(f"- **Summary**: {desc}")
            lines.append(f"- **Repository**: [{name}]({url})")
            lines.append(f"- **Deep Dive Command**: `last30days \"{name}\"`")
            lines.append("")
            rank += 1

        # 3. Product Launches
        if ph_results:
            lines.append("## 🚀 Fresh Product Launches (Product Hunt)")
            for p in ph_results[:3]:
                lines.append(f"- **[{p['title']}]({p['url']})**")
            lines.append("")

        return "\n".join(lines)
