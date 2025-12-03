"""
Scraper cog: wraps scrape_links.py and scrape_articles.py.
Prevents concurrent scrapes with asyncio.Lock.
Supports progress logging and category-specific scraping.
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from discord.ext import commands


logger = logging.getLogger("scraper_cog")

DATA_DIR = Path(__file__).parent.parent / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"
TODAY_LINKS_FILE = DATA_DIR / "today_links.json"

from scraper.scrape_links import main as scrape_links_main
from scraper.scrape_articles import main_async as scrape_articles_main_async
from scraper.scrape_links import CATEGORIES

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
                
                # Step 1: Fetch links
                msg = f"[SCRAPER] Step 1/2: Fetching links for {target}..."
                logger.info(msg)
                if progress_callback:
                    await progress_callback(msg)
                
                try:
                    # Call scrape_links directly
                    comparison = await scrape_links_main(categories=categories)
                    
                    msg = f"[SCRAPER] Found {comparison['total_articles']} articles ({comparison['new_articles']} new)"
                    logger.info(msg)
                    if progress_callback:
                        await progress_callback(msg)
                        
                except Exception as e:
                    error_msg = f"[SCRAPER] Links fetch failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    if progress_callback:
                        await progress_callback(error_msg)
                    return False

                # Step 2: Scrape articles
                msg = f"[SCRAPER] Step 2/2: Scraping article content for {target}..."
                logger.info(msg)
                if progress_callback:
                    await progress_callback(msg)

                try:
                    # Call scrape_articles async function directly (no asyncio.run)
                    await scrape_articles_main_async(
                        force=force,
                        categories=categories
                    )
                    
                    msg = "[SCRAPER] Article scraping completed!"
                    logger.info(msg)
                    if progress_callback:
                        await progress_callback(msg)
                        
                except Exception as e:
                    error_msg = f"[SCRAPER] Article scrape failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
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
        return list(CATEGORIES.keys())

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