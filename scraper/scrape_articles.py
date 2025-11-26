import argparse
import asyncio
import atexit
import json
import logging
import os
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

try:
    import jsonschema
    from jsonschema import validate

    JSONSCHEMA_AVAILABLE = True
except Exception:
    JSONSCHEMA_AVAILABLE = False

DATA_DIR = Path(__file__).parent.parent / "data"
TODAY_LINKS_FILE = DATA_DIR / "today_links.json"
ARTICLES_FILE = DATA_DIR / "articles.json"
ARTICLES_META_FILE = DATA_DIR / "articles_meta.json"
LOCK_FILE = DATA_DIR / "scrape_articles.lock"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("scrape_articles")


def atomic_write(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, str(path))
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        raise


def check_and_create_lock():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
            pid = int(payload.get("pid", 0))
            if pid:
                # check if process exists
                try:
                    os.kill(pid, 0)
                    logger.error(
                        "Lockfile exists and process %d is still running. Exiting.", pid
                    )
                    sys.exit(1)
                except OSError:
                    logger.info("Stale lockfile found (pid %d). Overwriting.", pid)
        except Exception:
            logger.info("Could not read existing lockfile, overwriting.")

    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "ts": time.time()}, f)


def remove_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


atexit.register(remove_lock)


def validate_today_links(data: Dict[str, Any]):
    if not JSONSCHEMA_AVAILABLE:
        return True
    schema = {
        "type": "object",
        "additionalProperties": {"type": "array", "items": {"type": "string"}},
    }
    try:
        validate(instance=data, schema=schema)
        return True
    except Exception as e:
        logger.warning("today_links.json failed validation: %s", e)
        return False


def load_cached_articles():
    if ARTICLES_FILE.exists():
        try:
            with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load cached articles: %s", e)
            return {}
    return {}


def get_cached_url_titles(articles: Dict[str, Any]):
    cached = set()
    for category_articles in articles.values():
        for article in category_articles:
            url = article.get("url") if isinstance(article, dict) else None
            if url:
                cached.add(url)
    return cached


async def fetch_article_details(
    page, url: str, timeout: int = 15000
) -> Dict[str, Any] | None:
    await page.goto(url, timeout=timeout)
    await page.wait_for_selector(".tdb-title-text", timeout=5000)
    title_el = await page.query_selector(".tdb-title-text")
    title_text = (await title_el.inner_text()).strip() if title_el else ""
    date_el = await page.query_selector("time.entry-date")
    datetime_attr = (
        await date_el.get_attribute("datetime") if date_el else "Unknown date"
    )

    contents_container = await page.query_selector(".vc_column_inner.tdi_84")
    content_text = ""
    if contents_container:
        ps = await contents_container.query_selector_all("p")
        paragraphs = []
        for p in ps:
            try:
                paragraphs.append((await p.inner_text()).strip())
            except Exception:
                continue
        content_text = "\n".join(paragraphs)

    featured_image_url = None
    featured_caption = None
    if contents_container:
        img = await contents_container.query_selector("img")
        figcap = await contents_container.query_selector("figcaption")
        if img:
            featured_image_url = await img.get_attribute("src")
        if figcap:
            featured_caption = await figcap.inner_text()

    return {
        "title": title_text,
        "date": datetime_attr,
        "content": content_text,
        "featured_image": featured_image_url,
        "featured_caption": featured_caption,
    }


async def fetch_with_retries(
    page, url: str, retries: int = 2, backoff_base: float = 1.0, timeout: int = 15000
):
    attempt = 0
    while True:
        try:
            return await fetch_article_details(page, url, timeout=timeout)
        except PlaywrightTimeoutError as e:
            attempt += 1
            if attempt > retries:
                logger.exception("Timeout fetching %s after %d attempts", url, attempt)
                return None
            wait = backoff_base * (2 ** (attempt - 1))
            logger.warning(
                "Timeout fetching %s, retrying in %.1fs (%d/%d)",
                url,
                wait,
                attempt,
                retries,
            )
            await asyncio.sleep(wait)
        except Exception as e:
            attempt += 1
            if attempt > retries:
                logger.exception(
                    "Error fetching %s after %d attempts: %s", url, attempt, e
                )
                return None
            wait = backoff_base * (2 ** (attempt - 1))
            logger.warning(
                "Error fetching %s, retrying in %.1fs (%d/%d): %s",
                url,
                wait,
                attempt,
                retries,
                e,
            )
            await asyncio.sleep(wait)


async def scrape_all_articles(
    force_rescrape: bool = False,
    concurrency: int = 5,
    timeout: int = 15000,
    retries: int = 2,
):
    if not TODAY_LINKS_FILE.exists():
        logger.error("Missing %s - run scrape_links.py first", TODAY_LINKS_FILE)
        return

    try:
        with open(TODAY_LINKS_FILE, "r", encoding="utf-8") as f:
            today_links = json.load(f)
    except Exception as e:
        logger.error("Failed to read today links: %s", e)
        return

    if not validate_today_links(today_links):
        logger.error("today_links.json failed validation. Aborting.")
        return

    # create lockfile
    check_and_create_lock()

    cached_articles = load_cached_articles()
    cached_urls = get_cached_url_titles(cached_articles)

    # Flatten links preserving category
    all_tasks = [(cat, url) for cat, urls in today_links.items() for url in urls]

    if not all_tasks:
        logger.info("No links found in %s", TODAY_LINKS_FILE)
        remove_lock()
        return

    if force_rescrape:
        to_scrape = all_tasks
        logger.info("Force rescrape enabled: scraping %d articles", len(to_scrape))
    else:
        to_scrape = [(c, u) for (c, u) in all_tasks if u not in cached_urls]
        skipped = len(all_tasks) - len(to_scrape)
        logger.info(
            "Found %d total links, %d new to scrape, %d cached (skipped)",
            len(all_tasks),
            len(to_scrape),
            skipped,
        )

    if not to_scrape:
        logger.info("Nothing to scrape. Use --force to rescrape cached items.")
        remove_lock()
        return

    semaphore = asyncio.Semaphore(concurrency)
    shutdown = False

    def _on_signal(sig, frame):
        nonlocal shutdown
        logger.warning("Received signal %s, stopping new work...", sig)
        shutdown = True

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    fetched = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page_pool = [
                await context.new_page()
                for _ in range(min(concurrency, len(to_scrape)))
            ]

            async def worker(index, category, link):
                async with semaphore:
                    if shutdown:
                        logger.debug("Shutdown set, skipping %s", link)
                        return (category, link, None)
                    page = page_pool[index % len(page_pool)]
                    article = await fetch_with_retries(
                        page, link, retries=retries, timeout=timeout
                    )
                    return (category, link, article)

            tasks = [worker(i, cat, url) for i, (cat, url) in enumerate(to_scrape)]
            fetched = await asyncio.gather(*tasks, return_exceptions=False)

            await asyncio.gather(*(p_.close() for p_ in page_pool))
            await browser.close()
    except Exception as e:
        logger.exception("Fatal error during scraping run: %s", e)
        remove_lock()
        return

    # Build resulting articles dict
    articles = {} if force_rescrape else cached_articles.copy()
    for cat in today_links.keys():
        articles.setdefault(cat, [])

    updated = 0
    for item in fetched:
        if not item:
            continue
        category, link, article_data = item
        if not article_data:
            continue
        articles[category] = [a for a in articles[category] if a.get("url") != link]
        entry = {
            "url": link,
            "title": article_data.get("title"),
            "date": article_data.get("date"),
            "content": article_data.get("content"),
            "featured_image": article_data.get("featured_image"),
            "featured_caption": article_data.get("featured_caption"),
        }
        articles[category].append(entry)
        updated += 1

    # Save articles atomically and metadata
    atomic_write(ARTICLES_FILE, articles)
    meta = {
        "scraped_at": time.time(),
        "scraped_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "user_agent": "playwright-python",
        "total_found": len(all_tasks),
        "updated": updated,
    }
    atomic_write(ARTICLES_META_FILE, meta)

    logger.info(
        "Scrape complete. Updated %d articles. Saved to %s", updated, ARTICLES_FILE
    )
    remove_lock()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape article pages from today_links.json"
    )
    parser.add_argument(
        "--force", action="store_true", dest="force", help="Force rescrape of all links"
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Number of concurrent page workers"
    )
    parser.add_argument("--timeout", type=int, default=15000, help="Page timeout in ms")
    parser.add_argument(
        "--retries", type=int, default=2, help="Retries for transient failures"
    )
    args = parser.parse_args()
    asyncio.run(
        scrape_all_articles(
            force_rescrape=args.force,
            concurrency=args.concurrency,
            timeout=args.timeout,
            retries=args.retries,
        )
    )
