"""GitHub source for repositories and discussions within the lookback window."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import urllib.parse

from .. import config
from ..http_client import default_client
from .base import BaseSource, SearchResult


class GitHubSource(BaseSource):
    name = "github"
    display_name = "GitHub"
    icon = "🐙"

    def search(self, query: str, lookback_days: int = 30, limit: int = 15) -> List[SearchResult]:
        """Search GitHub repositories pushed or active within the lookback window."""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        encoded_query = urllib.parse.quote_plus(f"{query} pushed:>{cutoff_date}")
        url = f"{config.GITHUB_API_BASE}/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page={limit}"

        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if config.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

        data = default_client.get_json(url, headers=headers, timeout=8) or {}
        items = data.get("items", [])

        results: List[SearchResult] = []
        for repo in items:
            name = repo.get("full_name") or ""
            html_url = repo.get("html_url") or ""
            desc = repo.get("description") or ""
            stars = repo.get("stargazers_count") or 0
            forks = repo.get("forks_count") or 0
            pushed_at = repo.get("pushed_at") or ""
            language = repo.get("language") or ""
            owner = repo.get("owner", {}).get("login") or ""

            results.append(
                SearchResult(
                    title=f"{name} ({language})" if language else name,
                    url=html_url,
                    text=desc,
                    author=owner,
                    date=pushed_at[:10],
                    source=self.name,
                    engagement={
                        "stars": stars,
                        "forks": forks,
                    },
                    metadata={
                        "language": language,
                        "stars": stars,
                    },
                )
            )

        return results

    def probe(self) -> Dict[str, Any]:
        """Probe GitHub search API."""
        start_time = datetime.now(timezone.utc)
        results = self.search("cli", lookback_days=7, limit=2)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if results:
            token_status = "authenticated" if config.GITHUB_TOKEN else "unauthenticated"
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"GitHub Search active ({token_status}, ping: {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "GitHub API failed or rate-limited",
        }
