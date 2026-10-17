"""Source registry and factory."""

from typing import Dict, List, Type

from .arxiv import ArxivSource
from .base import BaseSource, SearchResult
from .devto import DevToSource
from .github import GitHubSource
from .hackernews import HackerNewsSource
from .jina import JinaReader
from .polymarket import PolymarketSource
from .producthunt import ProductHuntSource
from .reddit import RedditSource
from .twitter import TwitterSource
from .web import WebSource
from .wikipedia import WikipediaSource
from .youtube import YouTubeSource

SOURCE_REGISTRY: Dict[str, Type[BaseSource]] = {
    "x": TwitterSource,
    "reddit": RedditSource,
    "youtube": YouTubeSource,
    "hackernews": HackerNewsSource,
    "web": WebSource,
    "github": GitHubSource,
    "polymarket": PolymarketSource,
    "arxiv": ArxivSource,
    "wikipedia": WikipediaSource,
    "devto": DevToSource,
    "producthunt": ProductHuntSource,
}

# Alias map for user convenience
SOURCE_ALIASES = {
    "twitter": "x",
    "hn": "hackernews",
    "yt": "youtube",
    "gh": "github",
    "papers": "arxiv",
    "prediction": "polymarket",
    "wiki": "wikipedia",
    "momentum": "wikipedia",
    "ph": "producthunt",
    "dev": "devto",
    "blogs": "devto",
}


def get_source(name: str) -> BaseSource:
    normalized = SOURCE_ALIASES.get(name.lower(), name.lower())
    if normalized not in SOURCE_REGISTRY:
        raise ValueError(f"Unknown source: {name}. Available: {list(SOURCE_REGISTRY.keys())}")
    return SOURCE_REGISTRY[normalized]()


def get_all_sources() -> List[BaseSource]:
    return [cls() for cls in SOURCE_REGISTRY.values()]
