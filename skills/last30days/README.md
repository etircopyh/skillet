# last30days (v4.1.0)

> A robust, zero-friction multi-source research engine powered by zero-key public proxies, mirrors, and alternative frontends.

Replaces brittle browser-cookie extraction and paid API requirements with reliable public proxies:
- **X (Twitter)**: Discovers tweets via DuckDuckGo and resolves full tweet JSON & engagement metrics via the **FxTwitter API** (`api.fxtwitter.com`).
- **Reddit**: Subreddit Atom/RSS feeds (`r/{sub}/search.rss`) + search dorking + Arctic Shift archive fallbacks.
- **YouTube**: Native `ytInitialData` parser extracting real-time view counts, channels, dates, and video metadata without needing `yt-dlp` or API keys.
- **Hacker News**: Real-time Algolia HN API with timestamp filtering down to the exact second (`numericFilters=created_at_i>...`).
- **Prediction Markets**: Polymarket Gamma public search API (`gamma-api.polymarket.com`) providing live consensus probabilities and betting odds.
- **Academic Papers**: Public arXiv Atom XML query API for recent preprints, author listings, and abstracts.
- **GitHub**: Search REST API with 30-day `pushed:>` filters and star rankings.
- **Wikipedia Momentum**: Wikimedia Pageviews API calculating 30-day velocity, trajectory changes, and ASCII sparklines (` ▂▃▅▆▇█`).
- **Dev.to Practitioner**: Dev.to REST API for hands-on technical tutorials, reviews, and developer reactions.
- **Product Hunt**: Product Hunt launch feed + dorks for fresh product launches and taglines.
- **Web & News**: Real-time Google News RSS + clean DuckDuckGo Lite table parser with zero tracking scripts.
- **Deep Reader**: **Jina Reader** (`r.jina.ai`) integration to bypass paywalls and extract clean markdown text from top articles.

---

## Quickstart

```bash
# Doctor check across all 11 endpoints + Jina
python3 skills/last30days/scripts/last30days.py doctor

# Run research
python3 skills/last30days/scripts/last30days.py "DeepSeek" --days 30

# Comparison Mode (A vs B)
python3 skills/last30days/scripts/last30days.py "Cursor vs Windsurf"

# Trend Radar & Discovery Mode
python3 skills/last30days/scripts/last30days.py "discover ai"

# Run with deep-reading on top articles
python3 skills/last30days/scripts/last30days.py "Claude 3.7 Sonnet" --deep

# Export standalone dark-theme HTML report
python3 skills/last30days/scripts/last30days.py "Claude 3.7" --html
```
