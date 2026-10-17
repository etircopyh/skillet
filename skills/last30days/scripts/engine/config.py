"""Configuration and environment variables for the last30days skill."""

import os
from pathlib import Path

# Package info
VERSION = "4.0.0"
SKILL_NAME = "last30days"

# Cache path
CACHE_DIR = Path(os.environ.get("LAST30DAYS_CACHE_DIR", Path.home() / ".cache" / "last30days"))
CACHE_DB_PATH = CACHE_DIR / "cache.db"
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour cache by default

# Lookback settings
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_TIMEOUT = 10  # Seconds per HTTP request

# User agents pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

# API Keys (Optional enhancements if present)
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN", "")).strip()
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
XAI_API_KEY = os.environ.get("XAI_API_KEY", "").strip()
SCRAPECREATORS_API_KEY = os.environ.get("SCRAPECREATORS_API_KEY", "").strip()

# Proxies & Mirrors endpoints
FXTWITTER_API_BASE = "https://api.fxtwitter.com"
TWITTER_SYNDICATION_BASE = "https://cdn.syndication.twimg.com"
HN_ALGOLIA_BASE = "https://hn.algolia.com/api/v1"
POLYMARKET_GAMMA_BASE = "https://gamma-api.polymarket.com"
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
GITHUB_API_BASE = "https://api.github.com"
JINA_READER_BASE = "https://r.jina.ai"
DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"
