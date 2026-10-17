"""Query intent classification and domain gating to eliminate noise on generic queries."""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class QueryPlanner:
    """Classifies user queries and routes them to relevant sources and subreddits."""

    MONEY_ADVICE_KEYWORDS = [
        "make money", "earn money", "side hustle", "get rich", "monetize",
        "passive income", "freelance", "online business", "make cash", "start a business"
    ]

    TECH_CODE_KEYWORDS = [
        "github", "library", "framework", "python", "typescript", "rust", "go",
        "api", "sdk", "cli", "code", "model", "llm", "ai", "benchmark"
    ]

    ACADEMIC_KEYWORDS = [
        "paper", "arxiv", "architecture", "algorithm", "dataset", "neural",
        "physics", "quantum", "mathematics", "theorem", "proof", "transformer"
    ]

    PREDICTION_KEYWORDS = [
        "odds", "prediction", "market", "election", "ipo", "rate cut", "fed",
        "crypto", "bitcoin", "stocks", "earnings", "box office", "sports", "will"
    ]

    @classmethod
    def analyze_query(cls, query: str) -> Dict[str, Any]:
        q_lower = query.lower()

        # Check for money / career / side hustle advice shape
        has_money_keyword = any(m in q_lower for m in ["money", "cash", "income", "wealth", "revenue"])
        has_action_keyword = any(a in q_lower for a in ["make", "earn", "build", "generate", "start", "get", "how"])
        is_money_advice = (has_money_keyword and has_action_keyword) or any(
            k in q_lower for k in [
                "side hustle", "passive income", "get rich", "monetize",
                "freelance", "online business", "start a business", "make a living"
            ]
        )
        is_academic = any(k in q_lower for k in cls.ACADEMIC_KEYWORDS)
        is_prediction = any(k in q_lower for k in cls.PREDICTION_KEYWORDS)
        is_tech = any(k in q_lower for k in cls.TECH_CODE_KEYWORDS)

        # Default: all sources
        enabled_sources = ["x", "reddit", "youtube", "hackernews", "web", "github", "polymarket", "arxiv"]
        target_subreddits = []
        expanded_queries = [query]

        if is_money_advice and not is_academic and not is_prediction:
            # Suppress noisy academic and prediction markets for broad money/advice questions
            enabled_sources = ["reddit", "youtube", "web", "hackernews", "x"]
            target_subreddits = ["sidehustle", "entrepreneur", "smallbusiness", "freelance"]
            expanded_queries = [
                query,
                "trending side hustles",
                "high demand freelance skills",
            ]

        return {
            "is_money_advice": is_money_advice,
            "is_academic": is_academic,
            "is_prediction": is_prediction,
            "enabled_sources": enabled_sources,
            "target_subreddits": target_subreddits,
            "expanded_queries": expanded_queries,
        }
