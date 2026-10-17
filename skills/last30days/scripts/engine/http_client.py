"""Resilient HTTP client using Python standard library with caching, retries, and UA rotation."""

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Union

from . import cache, config


class HttpClient:
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.cache = cache.default_cache

    def _get_random_ua(self) -> str:
        return random.choice(config.USER_AGENTS)

    def _build_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": self._get_random_ua(),
            "Accept": "*/*",
        }
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def request(
        self,
        method: str,
        url: str,
        data: Optional[Union[bytes, Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = config.DEFAULT_TIMEOUT,
        retries: int = 2,
        retry_delay: float = 1.0,
        cache_ttl: Optional[int] = config.DEFAULT_CACHE_TTL_SECONDS,
    ) -> Optional[str]:
        """Perform an HTTP request and return text. Never raises exceptions, returns None on failure."""
        method = method.upper()

        # Cache check for GET requests
        cache_key = f"{method}:{url}"
        if self.use_cache and method == "GET" and cache_ttl and cache_ttl > 0:
            cached_val = self.cache.get(cache_key)
            if cached_val is not None:
                return cached_val

        post_bytes = None
        if data is not None:
            if isinstance(data, dict):
                post_bytes = urllib.parse.urlencode(data).encode("utf-8")
            elif isinstance(data, bytes):
                post_bytes = data
            elif isinstance(data, str):
                post_bytes = data.encode("utf-8")

        req_headers = self._build_headers(headers)
        if post_bytes is not None and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        last_error = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(
                    url=url,
                    data=post_bytes if method in ("POST", "PUT", "PATCH") else None,
                    headers=req_headers,
                    method=method,
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_bytes = resp.read()
                    # Detect encoding from headers or default to utf-8
                    encoding = "utf-8"
                    content_type = resp.headers.get("content-type", "")
                    if "charset=" in content_type:
                        try:
                            encoding = content_type.split("charset=")[-1].split(";")[0].strip()
                        except Exception:
                            encoding = "utf-8"
                    text = resp_bytes.decode(encoding, errors="replace")

                    # Save to cache if GET and status 200
                    if self.use_cache and method == "GET" and cache_ttl and cache_ttl > 0:
                        self.cache.set(cache_key, text, ttl_seconds=cache_ttl)

                    return text
            except urllib.error.HTTPError as e:
                last_error = e
                # Retry on 429 Too Many Requests or 503 Service Unavailable
                if e.code in (429, 502, 503, 504) and attempt < retries:
                    wait_time = retry_delay * (2 ** attempt)
                    # Respect Retry-After header if provided
                    retry_after = e.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = min(float(retry_after), 10.0)
                    time.sleep(wait_time)
                    # Change UA for next attempt
                    req_headers["User-Agent"] = self._get_random_ua()
                    continue
                # For client errors (403, 404, etc.), don't retry fruitlessly
                break
            except Exception as e:
                last_error = e
                if attempt < retries:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                break

        return None

    def get_text(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = config.DEFAULT_TIMEOUT,
        cache_ttl: Optional[int] = config.DEFAULT_CACHE_TTL_SECONDS,
    ) -> Optional[str]:
        return self.request("GET", url, headers=headers, timeout=timeout, cache_ttl=cache_ttl)

    def get_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = config.DEFAULT_TIMEOUT,
        cache_ttl: Optional[int] = config.DEFAULT_CACHE_TTL_SECONDS,
    ) -> Optional[Any]:
        text = self.get_text(url, headers=headers, timeout=timeout, cache_ttl=cache_ttl)
        if text:
            try:
                return json.loads(text)
            except Exception:
                return None
        return None

    def post_text(
        self,
        url: str,
        data: Optional[Union[bytes, Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = config.DEFAULT_TIMEOUT,
    ) -> Optional[str]:
        return self.request("POST", url, data=data, headers=headers, timeout=timeout, cache_ttl=0)

    def post_json(
        self,
        url: str,
        json_data: Any,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = config.DEFAULT_TIMEOUT,
    ) -> Optional[Any]:
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        post_bytes = json.dumps(json_data).encode("utf-8")
        text = self.request("POST", url, data=post_bytes, headers=req_headers, timeout=timeout, cache_ttl=0)
        if text:
            try:
                return json.loads(text)
            except Exception:
                return None
        return None


# Default client instance
default_client = HttpClient()
