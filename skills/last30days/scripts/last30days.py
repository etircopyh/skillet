#!/usr/bin/env python3
"""last30days CLI — Multi-source research engine powered by zero-key proxies and mirrors."""

import argparse
import concurrent.futures
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to sys.path so engine can be imported directly
sys.path.insert(0, str(Path(__file__).parent))

from engine import config
from engine.comparison import ComparisonEngine, detect_comparison
from engine.discovery import DiscoveryEngine
from engine.doctor import run_doctor
from engine.html_export import HtmlExporter
from engine.http_client import default_client
from engine.planner import QueryPlanner
from engine.sources import JinaReader, SOURCE_REGISTRY, get_source
from engine.sources.base import SearchResult
from engine.synthesizer import Synthesizer


def slugify(text: str) -> str:
    """Convert text into a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


def run_research(
    topic: str,
    lookback_days: int = 30,
    selected_sources: Optional[List[str]] = None,
    deep_reading: bool = False,
    no_cache: bool = False,
) -> Dict[str, Any]:
    """Execute multi-source research across all enabled providers concurrently."""
    if no_cache:
        default_client.use_cache = False

    # Analyze query intent to filter noise (e.g. suppress arXiv/Polymarket on generic questions)
    plan = QueryPlanner.analyze_query(topic)
    active_sources = selected_sources if selected_sources is not None else plan["enabled_sources"]
    target_subs = plan.get("target_subreddits")

    results_by_source: Dict[str, List[SearchResult]] = {}

    def fetch_source(src_name: str):
        try:
            source = get_source(src_name)
            # Pass targeted subreddits to Reddit source if detected
            if src_name == "reddit" and target_subs:
                return src_name, source.search(topic, lookback_days=lookback_days, limit=12, subreddits=target_subs)
            return src_name, source.search(topic, lookback_days=lookback_days, limit=12)
        except Exception as e:
            sys.stderr.write(f"[{src_name}] Error: {e}\n")
            return src_name, []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_sources)) as executor:
        futures = [executor.submit(fetch_source, s) for s in active_sources]
        for f in concurrent.futures.as_completed(futures):
            src_name, items = f.result()
            results_by_source[src_name] = items

    # Deep reading with Jina Reader on top web articles if requested
    deep_articles = []
    if deep_reading:
        web_items = results_by_source.get("web", [])
        candidates = [item for item in web_items if item.url.startswith("http")][:2]
        if candidates:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                jina_futures = {
                    executor.submit(JinaReader.read_url, item.url): item
                    for item in candidates
                }
                for jf in concurrent.futures.as_completed(jina_futures):
                    try:
                        res = jf.result()
                        if res:
                            deep_articles.append(res)
                    except Exception:
                        pass

    return {
        "topic": topic,
        "lookback_days": lookback_days,
        "results": results_by_source,
        "deep_articles": deep_articles,
    }


def main():
    parser = argparse.ArgumentParser(
        description="last30days — Robust multi-source research engine utilizing zero-key proxies and mirrors."
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="Topic, question, comparison ('A vs B'), or 'discover [category]' (or 'doctor').",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=config.DEFAULT_LOOKBACK_DAYS,
        help=f"Lookback window in days (default: {config.DEFAULT_LOOKBACK_DAYS}).",
    )
    parser.add_argument(
        "--sources",
        "-s",
        type=str,
        help="Comma-separated list of sources (x,reddit,youtube,hackernews,web,github,polymarket,arxiv,wikipedia,devto,producthunt).",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Enable Jina Reader deep-reading for high-signal articles and papers.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON data instead of formatted markdown report.",
    )
    parser.add_argument(
        "--save",
        nargs="?",
        const="",
        help="Save report to markdown file. Defaults to '{topic}-last30days.md' if no filename given.",
    )
    parser.add_argument(
        "--html",
        nargs="?",
        const="",
        help="Export report to styled standalone HTML file. Defaults to '{topic}-last30days.html'.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run health check across all endpoints, proxies, and mirrors.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass SQLite cache and force fresh live queries.",
    )

    args = parser.parse_args()

    # Handle doctor subcommand or flag
    if args.doctor or (args.topic and args.topic.strip().lower() == "doctor"):
        run_doctor()
        sys.exit(0)

    if not args.topic:
        parser.print_help()
        sys.exit(1)

    raw_topic = args.topic.strip()

    # Handle 'discover' subcommand (e.g. 'discover ai', 'discover tech')
    if raw_topic.lower().startswith("discover"):
        parts = raw_topic.split(maxsplit=1)
        category = parts[1].strip() if len(parts) > 1 else "ai"
        report = DiscoveryEngine.discover_trends(category=category, lookback_days=args.days)
        print(report)
        if args.html is not None:
            html_file = args.html if args.html else f"discover-{category}-last30days.html"
            Path(html_file).write_text(HtmlExporter.export_html(report, title=f"Discovery: {category}"), encoding="utf-8")
            sys.stderr.write(f"\n[Exported HTML dashboard to {html_file}]\n")
        return

    # Handle Head-to-Head Comparison Mode (e.g. 'Cursor vs Windsurf')
    comp_entities = detect_comparison(raw_topic)
    if comp_entities:
        sys.stderr.write(f"[Comparison Mode detected: {' vs '.join(comp_entities)}]\n")
        entity_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(comp_entities)) as executor:
            future_to_entity = {
                executor.submit(run_research, e, args.days, None, args.deep, args.no_cache): e
                for e in comp_entities
            }
            for fut in concurrent.futures.as_completed(future_to_entity):
                ent = future_to_entity[fut]
                entity_results[ent] = fut.result()

        report = ComparisonEngine.format_comparison_report(comp_entities, entity_results, lookback_days=args.days)
        print(report)

        if args.html is not None:
            html_file = args.html if args.html else f"{slugify(raw_topic)}-last30days.html"
            Path(html_file).write_text(HtmlExporter.export_html(report, title=raw_topic), encoding="utf-8")
            sys.stderr.write(f"\n[Exported HTML dashboard to {html_file}]\n")
        if args.save is not None:
            md_file = args.save if args.save else f"{slugify(raw_topic)}-last30days.md"
            Path(md_file).write_text(report, encoding="utf-8")
            sys.stderr.write(f"\n[Saved report to {md_file}]\n")
        return

    # Standard single-topic research
    sources_list = None
    if args.sources:
        sources_list = [s.strip().lower() for s in args.sources.split(",") if s.strip()]

    data = run_research(
        topic=raw_topic,
        lookback_days=args.days,
        selected_sources=sources_list,
        deep_reading=args.deep,
        no_cache=args.no_cache,
    )

    if args.json:
        serializable = {
            "topic": data["topic"],
            "lookback_days": data["lookback_days"],
            "deep_articles": data["deep_articles"],
            "results": {
                src: [item.to_dict() for item in items]
                for src, items in data["results"].items()
            },
        }
        json_output = json.dumps(serializable, indent=2, ensure_ascii=False)
        print(json_output)
        if args.save is not None:
            filename = args.save if args.save else f"{slugify(raw_topic)}-last30days.json"
            Path(filename).write_text(json_output, encoding="utf-8")
            sys.stderr.write(f"\n[Saved JSON data to {filename}]\n")
        return

    # Synthesize markdown report
    report = Synthesizer.format_report(
        topic=data["topic"],
        results_by_source=data["results"],
        lookback_days=data["lookback_days"],
        deep_readings=data["deep_articles"],
    )

    print(report)

    if args.html is not None:
        html_file = args.html if args.html else f"{slugify(raw_topic)}-last30days.html"
        Path(html_file).write_text(HtmlExporter.export_html(report, title=raw_topic), encoding="utf-8")
        sys.stderr.write(f"\n[Exported HTML dashboard to {html_file}]\n")

    if args.save is not None:
        filename = args.save if args.save else f"{slugify(raw_topic)}-last30days.md"
        Path(filename).write_text(report, encoding="utf-8")
        sys.stderr.write(f"\n[Saved report to {filename}]\n")


if __name__ == "__main__":
    main()
