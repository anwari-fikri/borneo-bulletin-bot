"""
Scraper cog: wraps scrape_links.py and scrape_articles.py.
Prevents concurrent scrapes with asyncio.Lock.
Supports progress logging and category-specific scraping.
"""
import asyncio
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from discord.ext import commands
import discord

logger = logging.getLogger("scraper_cog")

DATA_DIR = Path(__file__).parent.parent / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"
TODAY_LINKS_FILE = DATA_DIR / "today_links.json"


class ScraperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._scrape_lock = asyncio.Lock()

    async def run_scraper(self, force: bool = False, categories: list = None, progress_callback=None):
        """
        Run scraper pipeline (links → articles). Prevent concurrent runs with lock.
        
        Args:
            force: Force rescrape all articles
            categories: List of categories to scrape, or None for all
            progress_callback: Async function(message) for progress updates
        """
        async with self._scrape_lock:
            try:
                target = f"categories: {', '.join(categories)}" if categories else "all categories"
                msg = f"[SCRAPER] Starting scrape for {target}..."
                logger.info(msg)
                if progress_callback:
                    await progress_callback(msg)
                
                # Run scrape_links.py
                msg = f"[SCRAPER] Step 1/2: Fetching links for {target}..."
                logger.info(msg)
                if progress_callback:
                    await progress_callback(msg)
                
                cmd_links = ["poetry", "run", "python", "scraper/scrape_links.py"]
                if categories:
                    cmd_links.append(",".join(categories))
                
                result = await self._run_command(cmd_links, progress_callback)
                if result != 0:
                    error_msg = f"[SCRAPER] Links fetch failed (code {result})"
                    logger.error(error_msg)
                    if progress_callback:
                        await progress_callback(error_msg)
                    return False

                # Run scrape_articles.py
                msg = f"[SCRAPER] Step 2/2: Scraping articles for {target}..."
                logger.info(msg)
                if progress_callback:
                    await progress_callback(msg)
                
                cmd_articles = ["poetry", "run", "python", "scraper/scrape_articles.py"]
                if force:
                    cmd_articles.append("--force")
                if categories:
                    cmd_articles.extend(["--categories", ",".join(categories)])
                
                result = await self._run_command(cmd_articles, progress_callback)
                if result != 0:
                    error_msg = f"[SCRAPER] Article scrape failed (code {result})"
                    logger.error(error_msg)
                    if progress_callback:
                        await progress_callback(error_msg)
                    return False

                msg = "[SCRAPER] Scrape completed successfully!"
                logger.info(msg)
                if progress_callback:
                    await progress_callback(msg)
                return True
            except Exception as e:
                error_msg = f"[SCRAPER] Error: {str(e)}"
                logger.exception(error_msg)
                if progress_callback:
                    await progress_callback(error_msg)
                return False

    async def _run_command(self, cmd, progress_callback=None):
        """Run a shell command asynchronously with progress streaming."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Stream stdout in real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                text = line.decode().strip()
                if text and progress_callback:
                    await progress_callback(text)
            
            stdout, stderr = await process.communicate()
            
            # Log any stderr
            if stderr:
                err_text = stderr.decode().strip()
                logger.warning("Command stderr: %s", err_text)
            
            return process.returncode
        except Exception as e:
            logger.exception("Command execution error: %s", e)
            return 1

    def load_articles(self):
        """Load articles.json from disk. Return dict or empty dict on error."""
        if ARTICLES_FILE.exists():
            try:
                with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load articles.json: %s", e)
                return {}
        return {}

    def get_categories(self):
        """Return list of available categories."""
        articles = self.load_articles()
        return list(articles.keys())

    def get_articles_for_category(self, category: str):
        """Get articles for a specific category."""
        articles = self.load_articles()
        return articles.get(category, [])

    def is_today(self, date_str: str) -> bool:
        """Check if date string contains today's date (simple check)."""
        if not date_str:
            return False
        today = datetime.now().strftime("%Y-%m-%d")
        return today in date_str


async def setup(bot):
    await bot.add_cog(ScraperCog(bot))
