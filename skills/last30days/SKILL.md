---
name: last30days
version: "4.1.0"
description: "Research what people actually say about any topic, technology, company, person, or product over the last 30 days. Powered by zero-key public proxies, mirrors, and alternative frontends: FxTwitter for X, Reddit RSS feeds & dorks, native YouTube ytInitialData extraction, Algolia Hacker News, Polymarket prediction odds, arXiv preprints, GitHub repositories, Wikipedia momentum curves, Dev.to practitioner tutorials, Product Hunt launches, and Jina Reader (r.jina.ai) deep reading."
argument-hint: 'last30days <topic> [--days 30] [--sources x,reddit,youtube,hn,web,github,polymarket,arxiv,wikipedia,devto,producthunt] [--deep] [--html]'
allowed-tools: Bash, Read, Write, AskUserQuestion, WebSearch
user-invocable: true
metadata:
  tags:
    - research
    - deep-research
    - recency
    - sentiment
    - social-media
    - multi-source
    - twitter
    - reddit
    - youtube
    - hackernews
    - polymarket
    - arxiv
    - github
    - wikipedia
    - devto
    - producthunt
    - comparison
    - discovery
---

# `last30days` — Zero-Key Multi-Source Research Engine

A robust, resilient, zero-friction research engine designed to capture community consensus, debate, news, market signals, velocity trends, and practitioner tutorials over a 30-day window without relying on brittle browser cookies, node dependencies, or paid API keys.

---

## Architecture & Proxy Arsenal

Every platform is queried concurrently using high-reliability public proxies, alternative frontends, and native scrapers:

| Platform | Primary Trick / Proxy | Secondary Fallback | Signals Extracted |
| :--- | :--- | :--- | :--- |
| **X (Twitter)** | `api.fxtwitter.com/status/:id` + DDG site dorks | `cdn.syndication.twimg.com` | Full tweet text, author `@handle`, likes, retweets, replies, quotes |
| **Reddit** | Subreddit RSS feeds (`r/{sub}/search.rss`) | DDG `site:reddit.com/r/` dorks & Arctic Shift | Post titles, author, text snippets, discussion permalinks |
| **YouTube** | Native `ytInitialData` extraction from search HTML | Invidious API mirrors | Video titles, channel name, exact view counts, upload dates, descriptions |
| **Hacker News** | Algolia HN Search API (`hn.algolia.com/api/v1`) | Algolia `tags=comment` | Top stories, points, comment counts, direct community quotes |
| **Prediction Markets** | Polymarket Gamma Public Search (`gamma-api.polymarket.com`) | Events & Markets endpoint | Real-money prediction probabilities, binary outcome percentages, volumes |
| **Academic Papers** | arXiv Atom XML Export API (`export.arxiv.org/api/query`) | Direct arXiv search | Paper title, authors, abstracts, arXiv IDs, PDF links |
| **Engineering / Code** | GitHub REST Search API (`api.github.com/search/repositories`) | `gh` CLI if authenticated | Stargazers, forks, primary language, latest pushed_at date |
| **Wikipedia Momentum** | Wikimedia Pageviews API (`wikimedia.org/api/rest_v1/...`) | Search API | 30-day view velocity, trajectory % changes, ASCII sparklines (` ▂▃▅▆▇█`) |
| **Dev.to Practitioner** | Dev.to REST API (`dev.to/api/articles?tag=...`) | Keyword search | Technical tutorials, hands-on reviews, practitioner reactions & comments |
| **Product Hunt** | Product Hunt launch feed + DDG launch dorks | Topic launches | Launch headlines, product taglines, maker links |
| **Web & News** | Google News RSS feed + DuckDuckGo Lite parser | Brave Search (if `BRAVE_API_KEY` set) | Real-time breaking news headlines, organic articles, publisher domains |
| **Deep Reader** | Jina Reader (`r.jina.ai/:url`) | Direct HTTP client | Full article markdown body, bypasses paywalls and ad bloat |

---

## Modes & Features

### 1. Standard Research Mode
Query all sources concurrently with automatic query planning (e.g. general career/money topics automatically suppress noisy academic/prediction markets and route to `r/sidehustle` or `r/entrepreneur`):
```bash
python3 skills/last30days/scripts/last30days.py "Anthropic Claude"
```

### 2. Comparison Mode (`A vs B`)
Automatically triggered when the query contains ` vs ` (or `--vs`). Runs parallel research for both entities and generates a side-by-side comparison matrix, platform sentiment takes, and a consensus verdict:
```bash
python3 skills/last30days/scripts/last30days.py "Cursor vs Windsurf" --days 14
```

### 3. Discovery Mode (`discover [category]`)
Scans Hacker News, trending GitHub repos, and Product Hunt for breakout topics and viral trends over the last 30 days:
```bash
python3 skills/last30days/scripts/last30days.py "discover ai"
python3 skills/last30days/scripts/last30days.py "discover devtools"
```

### 4. Standalone Dark-Mode HTML Export (`--html`)
Generates an elegant, fully styled, standalone dark-theme HTML report with KPI cards, source badges, and direct links:
```bash
python3 skills/last30days/scripts/last30days.py "Claude 3.7" --html
```

### 5. Jina Deep Reading (`--deep`)
Fetches and reads full markdown bodies of top articles via Jina Reader (`r.jina.ai`), bypassing paywalls and extracts actionable summaries.
```bash
python3 skills/last30days/scripts/last30days.py "OpenAI o3 reasoning" --deep
```

---

## CLI Options

```bash
# General research (default 30 days across all sources)
python3 skills/last30days/scripts/last30days.py "Anthropic Claude"

# Custom lookback window (e.g. 7 days or 90 days)
python3 skills/last30days/scripts/last30days.py "Nvidia Blackwell" --days 7

# Filter specific sources
python3 skills/last30days/scripts/last30days.py "React 19" --sources x,reddit,youtube,hn,wikipedia,devto

# Comparison mode
python3 skills/last30days/scripts/last30days.py "PyTorch vs JAX"

# Trend radar discovery
python3 skills/last30days/scripts/last30days.py "discover"

# Export styled HTML dashboard
python3 skills/last30days/scripts/last30days.py "DeepSeek V3" --html

# Output raw JSON for programmatic workflows
python3 skills/last30days/scripts/last30days.py "DeepSeek V3" --json

# Run health diagnostics across all endpoints
python3 skills/last30days/scripts/last30days.py doctor
```

---

## Agent Invocation Protocol

When a user asks:
- *"What are people saying about X?"*
- *"What's the consensus on X over the last month?"*
- *"Compare X vs Y recently"*
- *"What's trending in [category]?"*
- *"Run last30days on X"*

### Step 1: Execute the Engine
Run the engine via bash:
```bash
# Standard topic
python3 skills/last30days/scripts/last30days.py "<topic>" --days 30

# Comparison topic
python3 skills/last30days/scripts/last30days.py "<entity A> vs <entity B>"

# Discovery / trends
python3 skills/last30days/scripts/last30days.py "discover <category>"
```
*(Add `--deep` if the user wants thorough article/paper excerpts; add `--html` if an export dashboard is requested).*

### Step 2: Relay the High-Signal Output
1. **Mandatory First Line:** The response must begin with the badge emitted by the engine:
   ```
   🌐 last30days v4.1.0 · synced {YYYY-MM-DD} · window: {N} days
   ```
2. **Present Ground Truth:** State the clear consensus, the main controversy/debate, and key numbers (e.g. Polymarket odds, GitHub stars, video views, Wikipedia velocity).
3. **Preserve Quotes & Handles:** Include verbatim community quotes with exact author handles and upvote/like numbers.
4. **Verified Links:** Include clickable links `[Title](url)` to evidence.

---

## Caching & Health Check

- All queries are cached in a local SQLite database (`~/.cache/last30days/cache.db`) with an automatic 1-hour TTL to prevent redundant requests and respect rate limits.
- Use `--no-cache` to force fresh live queries.
- Run `python3 skills/last30days/scripts/last30days.py doctor` at any time to verify proxy connectivity and measure round-trip latencies across all 11 sources + Jina Reader.
