"""Diagnostics and doctor health check for last30days."""

import concurrent.futures
from datetime import datetime, timezone
import sys
from typing import Any, Dict, List

from . import config
from .sources import SOURCE_REGISTRY, JinaReader, get_all_sources


def run_doctor() -> Dict[str, Any]:
    """Execute live probes across all sources and print a diagnostic report."""
    print(f"\n🩺 last30days Doctor (v{config.VERSION})")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Cache DB: {config.CACHE_DB_PATH}")
    print("-" * 65)

    # Detect optional keys
    env_keys = []
    if config.BRAVE_API_KEY:
        env_keys.append("BRAVE_API_KEY ✓")
    if config.GITHUB_TOKEN:
        env_keys.append("GITHUB_TOKEN ✓")
    if config.OPENAI_API_KEY:
        env_keys.append("OPENAI_API_KEY ✓")
    if config.PERPLEXITY_API_KEY:
        env_keys.append("PERPLEXITY_API_KEY ✓")
    if config.XAI_API_KEY:
        env_keys.append("XAI_API_KEY ✓")
    if config.SCRAPECREATORS_API_KEY:
        env_keys.append("SCRAPECREATORS_API_KEY ✓")

    keys_str = ", ".join(env_keys) if env_keys else "None (Zero-key pure proxy mode)"
    print(f"Configured Credentials: {keys_str}\n")
    print("Running parallel probes across sources and proxies...")

    results = {}
    sources = get_all_sources()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_src = {executor.submit(src.probe): src for src in sources}
        # Also probe Jina Reader
        jina_future = executor.submit(JinaReader.probe)

        for future in concurrent.futures.as_completed(future_to_src):
            src = future_to_src[future]
            try:
                res = future.result()
                results[src.name] = (src, res)
            except Exception as e:
                results[src.name] = (src, {"status": "ERROR", "latency_ms": -1, "details": str(e)})

        try:
            jina_res = jina_future.result()
        except Exception as e:
            jina_res = {"status": "ERROR", "latency_ms": -1, "details": str(e)}

    # Display Source Results
    print("\nSource Probes:")
    working = 0
    degraded = 0
    failed = 0

    for name in ["x", "reddit", "youtube", "hackernews", "web", "github", "polymarket", "arxiv", "wikipedia", "devto", "producthunt"]:
        if name not in results:
            continue
        src, probe = results[name]
        status = probe.get("status", "UNKNOWN")
        latency = probe.get("latency_ms", -1)
        details = probe.get("details", "")

        if status == "OK":
            working += 1
            icon = "● \033[32mOK\033[0m"
        elif status == "DEGRADED":
            degraded += 1
            icon = "◐ \033[33mDEGRADED\033[0m"
        else:
            failed += 1
            icon = "✕ \033[31mERROR\033[0m"

        lat_str = f"({latency}ms)" if latency > 0 else ""
        print(f"  {icon:<14} {src.icon} {src.display_name:<16} {lat_str:<10} {details}")

    # Display Jina Reader
    j_status = jina_res.get("status")
    j_lat = jina_res.get("latency_ms", -1)
    j_det = jina_res.get("details", "")
    j_icon = "● \033[32mOK\033[0m" if j_status == "OK" else "✕ \033[31mERROR\033[0m"
    j_lat_str = f"({j_lat}ms)" if j_lat > 0 else ""
    print(f"  {j_icon:<14} 📖 Jina Deep Reader  {j_lat_str:<10} {j_det}")

    print("-" * 65)
    print(f"Summary: {working} OK, {degraded} Degraded, {failed} Failed")
    if failed == 0:
        print("🚀 All systems operational! Zero-key proxies and scrapers ready.")
    else:
        print("⚠️ Some sources encountered errors. Check proxy connectivity.")

    return {
        "sources": {k: v[1] for k, v in results.items()},
        "jina": jina_res,
        "summary": {"working": working, "degraded": degraded, "failed": failed},
    }


if __name__ == "__main__":
    run_doctor()
