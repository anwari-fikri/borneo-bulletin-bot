[I cant fix this cloudflare blocking my scraping when i host it on my VPS. I can run this on my main PC though]

# Borneo Bulletin Discord Bot

A Discord bot that fetches and shares latest news from Borneo Bulletin. The repository contains the scraper pipeline that collects articles daily.

**[Invite Bot to Your Server](https://discord.com/oauth2/authorize?client_id=1097394756985819136)** — Click to add the bot to your Discord server.

## Overview

- **Scraper** (`scraper/` directory): Collects today's article links and extracts full article content (title, date, content, featured image).
- **Bot** (`bot.py` + `cogs/`): Discord bot with commands for news, subscriptions, and scheduled posts.
- **Digests**: Daily 9 AM GMT+8 scheduled posts send compact digests (title + excerpt) for each category you're subscribed to.

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

- `/read_full [category]` - Read full articles for today in a thread (auto-scrapes if needed; shows all articles for category)
- `/send_digest [category]` - Send a compact digest to this channel (if no category provided, sends digests for all your subscribed categories)
- `/categories` - List available news categories

**Subscriptions:**

- `/subscribe [category]` - Subscribe to a category (or use `all` to subscribe to all categories at once)
- `/unsubscribe [category]` - Unsubscribe from a category
- `/subscriptions` - Show your current subscriptions

**Schedule:**

- `/toggle_scheduled_news [on|off]` - Enable or disable daily 9 AM GMT+8 scheduled digests for your subscribed categories (requires at least 1 subscription)

**Utility:**

- `/ping` - Check bot latency
- `/commands` - Show all available commands and usage

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

### Deployment

#### Self-Hosted VPS (AWS, DigitalOcean, Azure)

1. SSH into server
2. Install Docker + Docker Compose
3. Clone repo: `git clone https://github.com/anwari-fikri/borneo-bulletin-bot.git`
4. `cd borneo-bulletin-bot && docker-compose up -d`
5. Bot runs 24/7

### Environment Variables

Set in `.env` or via `docker-compose.yml`:

- `DISCORD_TOKEN` - Your bot token (required)
