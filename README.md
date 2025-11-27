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

## Docker Deployment

### Quick Start with Docker Compose

1. **Prerequisites**: Install [Docker](https://www.docker.com/products/docker-desktop) and [Docker Compose](https://docs.docker.com/compose/install/).

2. **Create `.env` file**:

```powershell
copy .env.example .env
# Edit .env and add your DISCORD_TOKEN
```

3. **Build and run**:

```powershell
docker-compose up -d
```

4. **View logs**:

```powershell
docker-compose logs -f bot
```

5. **Stop the bot**:

```powershell
docker-compose down
```

### Manual Docker Build

Build the image:

```bash
docker build -t borneo-bulletin-bot:latest .
```

Run the container:

```bash
docker run -d \
  --name borneo-bot \
  -e DISCORD_TOKEN=your_token_here \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  borneo-bulletin-bot:latest
```

View logs:

```bash
docker logs -f borneo-bot
```

### Deployment Platforms

#### Railway (Recommended)

1. Push to GitHub (`git push`)
2. Connect repo at [railway.app](https://railway.app)
3. Add `DISCORD_TOKEN` environment variable
4. Deploy — Railway auto-detects Dockerfile
5. Bot runs 24/7 on free tier (limited hours)

#### Heroku (Legacy)

```bash
heroku container:push web
heroku container:release web
```

#### Self-Hosted VPS (AWS, DigitalOcean, Azure)

1. SSH into server
2. Install Docker + Docker Compose
3. Clone repo: `git clone https://github.com/anwari-fikri/borneo-bulletin-bot.git`
4. `cd borneo-bulletin-bot && docker-compose up -d`
5. Bot runs 24/7

### Data Persistence

Docker volumes mount `./data` folder to container `/app/data`:

- Articles, links, and subscription data persist across restarts
- Logs are mounted to `./logs`

**Backup your data**:

```bash
docker cp borneo-bot:/app/data ./data-backup
```

### Environment Variables

Set in `.env` or via `docker-compose.yml`:

- `DISCORD_TOKEN` - Your bot token (required)
- `IMAGE_PROXY_BASE` - Optional image proxy URL (e.g., `http://proxy:8000`)
- `TZ` - Timezone for scheduler (default: `Asia/Kuala_Lumpur` for GMT+8)

### Troubleshooting Docker

**Bot keeps restarting:**

```bash
docker-compose logs bot
# Check for DISCORD_TOKEN or connection errors
```

**Permission denied on volumes:**

```bash
chmod -R 755 ./data
```

**Out of disk space:**

```bash
docker system prune -a  # Remove unused images
```

## Troubleshooting

- **Playwright error**: run `poetry run playwright install`
- **Lockfile blocks run**: check/remove `data/*.lock` if stale
- **Slow runs**: lower `--concurrency` or raise `--timeout`
- **Docker build fails**: ensure `poetry.lock` exists (`poetry lock` to regenerate)
