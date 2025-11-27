# Borneo Bulletin Discord Bot

A Discord bot that fetches and shares latest news from Borneo Bulletin. The repository contains the scraper pipeline that collects articles daily.

## Overview

- **Scraper** (`scraper/` directory): Collects today's article links and extracts full article content (title, date, content, featured image).
- **Bot** (`bot.py` + `cogs/`): Discord bot with commands for news, subscriptions, and scheduled posts.

## Setup

Install dependencies:

```powershell
poetry install
poetry run playwright install
```

Create `.env` from template:

```powershell
copy .env.example .env
```

Add your Discord bot token to `.env`:

```
DISCORD_TOKEN=your_token_here
```

## Bot Usage

Run the bot:

```powershell
poetry run python bot.py
```

### Commands

**News:**

- `/get_todays_news [category]` - Get today's news (auto-scrapes if needed)
- `/latest [category] [count]` - Get latest 1-3 articles
- `/categories` - List available categories

**Subscriptions:**

- `/subscribe [category]` - Subscribe to a category
- `/unsubscribe [category]` - Unsubscribe
- `/subscriptions` - Show your subscriptions

**Schedule:**

- `/toggle_scheduled_news [all/category]` - Toggle daily 9 AM GMT+8 posts

**Utility:**

- `/ping` - Check bot latency
- `/commands` - Show all commands

## Scraper Usage

Collect links:

```powershell
poetry run python .\scraper\scrape_links.py
```

Scrape articles (only new ones):

```powershell
poetry run python .\scraper\scrape_articles.py
```

Force re-scrape all:

```powershell
poetry run python .\scraper\scrape_articles.py --force
```

CLI options:

- `--force` : re-scrape everything
- `--concurrency N` : concurrent workers (default 5)
- `--timeout MS` : page timeout in ms (default 15000)
- `--retries N` : retry attempts (default 2)

## Data Files

- `data/today_links.json` : links discovered today
- `data/articles.json` : full article data (title, date, content, image)
- `data/*.json.example` : templates

### Subscription JSON example

The bot stores user subscriptions as a mapping of Discord user ID (string) to an array of category names. An example template is provided at `data/user_subscriptions.json.example`.

Example content:

```json
{
  "172365512834023436": ["national"],
  "123456789012345678": ["national", "sports"],
  "987654321098765432": ["business"]
}
```

Notes:

- Do NOT commit your real `data/user_subscriptions.json` if it contains private user IDs — use the `.example` template for public examples.
- To manually edit subscriptions, update the JSON and restart the bot, or use the bot's `/subscribe` and `/unsubscribe` commands.

## Features

- **Atomic writes**: JSON saved safely; no corruption on crashes
- **Lockfile protection**: prevents overlapping runs
- **Retries + backoff**: handles transient failures
- **Graceful shutdown**: listens to SIGINT/SIGTERM
- **Schema validation**: optional `jsonschema` checks
- **Structured logging**: timestamps and log levels

## Troubleshooting

- **Playwright error**: run `poetry run playwright install`
- **Lockfile blocks run**: check/remove `data/*.lock` if stale
- **Slow runs**: lower `--concurrency` or raise `--timeout`
