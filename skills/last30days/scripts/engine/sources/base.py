"""Base classes and data models for last30days sources."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    title: str
    url: str
    text: str = ""
    author: str = ""
    date: str = ""
    source: str = ""  # 'x', 'reddit', 'youtube', 'hackernews', 'web', 'github', 'polymarket', 'arxiv'
    engagement: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseSource(ABC):
    """Abstract base source for all data providers."""

    name: str = "base"
    display_name: str = "Base Source"
    icon: str = "🔍"

    @abstractmethod
    def search(self, query: str, lookback_days: int = 30, limit: int = 15) -> List[SearchResult]:
        """Perform search and return list of SearchResult objects."""
        pass

    def probe(self) -> Dict[str, Any]:
        """Diagnostic probe for doctor check."""
        try:
            start_time = datetime.now(timezone.utc)
            results = self.search("test", lookback_days=30, limit=2)
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return {
                "status": "OK" if len(results) > 0 else "EMPTY",
                "latency_ms": round(duration_ms, 1),
                "count": len(results),
                "details": f"Yielded {len(results)} items in {round(duration_ms)}ms",
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "latency_ms": -1,
                "count": 0,
                "details": str(e),
            }
