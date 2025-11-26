# Borneo Bulletin Discord Bot

A Discord bot that fetches and shares latest news from Borneo Bulletin. The repository contains the scraper pipeline that collects articles daily.

## Overview

- **Scraper** (`scraper/` directory): Collects today's article links and extracts full article content (title, date, content, featured image).
- **Bot** (not implemented yet): Will post new articles to Discord channels.

## Quick Start

```powershell
poetry install
poetry run playwright install
```

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
