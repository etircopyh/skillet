"""Jina Reader integration (r.jina.ai) for deep reading and content extraction."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional

from .. import config
from ..http_client import default_client


class JinaReader:
    """Uses r.jina.ai to pull clean, paywall-bypassed markdown content from URLs."""

    @classmethod
    def read_url(cls, target_url: str, max_chars: int = 4000) -> Optional[Dict[str, Any]]:
        """Fetch full webpage content converted to markdown."""
        if not target_url.startswith("http"):
            return None

        # Build Jina Reader URL
        reader_url = f"{config.JINA_READER_BASE}/{target_url}"
        headers = {
            "Accept": "text/markdown,text/plain",
            "X-No-Cache": "false",
        }
        text = default_client.get_text(reader_url, headers=headers, timeout=12)
        if not text:
            return None

        # Check for error or blocked interstitial
        if "Warning: Target URL returned error 403" in text or "Warning: Target URL returned error 404" in text:
            return None

        # Extract title if present
        title_match = re.search(r"^Title:\s*(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else ""

        # Extract published date if present
        date_match = re.search(r"^Published Time:\s*(.+)$", text, re.MULTILINE)
        published_date = date_match.group(1).strip() if date_match else ""

        # Extract markdown content body
        content_marker = "Markdown Content:"
        content = text
        if content_marker in text:
            content = text.split(content_marker, 1)[-1].strip()

        # Truncate to reasonable character bound
        trimmed_content = content[:max_chars].strip()

        return {
            "title": title,
            "url": target_url,
            "published_date": published_date,
            "content": trimmed_content,
            "char_count": len(trimmed_content),
        }

    @classmethod
    def probe(cls) -> Dict[str, Any]:
        """Diagnostic probe for Jina Reader."""
        start_time = datetime.now(timezone.utc)
        res = cls.read_url("https://example.com", max_chars=500)
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if res and res.get("content"):
            return {
                "status": "OK",
                "latency_ms": round(duration_ms, 1),
                "count": 1,
                "details": f"Jina Reader proxy active (ping: {round(duration_ms)}ms)",
            }
        return {
            "status": "ERROR",
            "latency_ms": -1,
            "count": 0,
            "details": "Jina Reader proxy failed",
        }
