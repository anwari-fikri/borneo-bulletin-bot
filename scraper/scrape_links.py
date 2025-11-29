import asyncio
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Map categories to their pagination container IDs
CATEGORIES = {
    "national": {
        "url": "https://borneobulletin.com.bn/category/national/",
        "pagination_tdi": "#tdi_106",
    },
    "southeast": {
        "url": "https://borneobulletin.com.bn/category/southeast/",
        "pagination_tdi": "#tdi_107",
    },
    "world": {
        "url": "https://borneobulletin.com.bn/category/world/",
        "pagination_tdi": "#tdi_106",
    },
    "business": {
        "url": "https://borneobulletin.com.bn/category/business/",
        "pagination_tdi": "#tdi_107",
    },
    "tech": {
        "url": "https://borneobulletin.com.bn/category/tech/",
        "pagination_tdi": "#tdi_107",
    },
    "lifstyle": {
        "url": "https://borneobulletin.com.bn/category/lifstyle/",
        "pagination_tdi": "#tdi_107",
    },
    "entertainment": {
        "url": "https://borneobulletin.com.bn/category/entertainment/",
        "pagination_tdi": "#tdi_107",
    },
    "sports": {
        "url": "https://borneobulletin.com.bn/category/sports/",
        "pagination_tdi": "#tdi_106",
    },
    "opinion": {
        "url": "https://borneobulletin.com.bn/category/opinion/",
        "pagination_tdi": "#tdi_106",
    },
    # Add more categories here
}

DATA_DIR = Path(__file__).parent.parent / "data"
TODAY_LINKS_FILE = DATA_DIR / "today_links.json"
PREVIOUS_LINKS_FILE = DATA_DIR / "previous_links.json"
LOCK_FILE = DATA_DIR / "scrape_links.lock"
LINKS_META_FILE = DATA_DIR / "today_links_meta.json"


def check_and_create_lock():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                payload = json.load(f)
            pid = int(payload.get("pid", 0))
            if pid:
                try:
                    os.kill(pid, 0)
                    print(
                        f"Lockfile exists and process {pid} is still running. Exiting."
                    )
                    raise SystemExit(1)
                except OSError:
                    print(f"Stale lockfile found (pid {pid}). Overwriting.")
        except Exception:
            print("Could not read existing lockfile, overwriting.")

    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "ts": time.time()}, f)


def remove_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


import atexit

atexit.register(remove_lock)
LINKS_META_FILE = DATA_DIR / "today_links_meta.json"


def atomic_write(path: Path, data):
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


TOP_ARTICLES_SELECTOR = ".vc_row_inner.tdi_80.vc_row.vc_inner.wpb_row.td-pb-row"
TODAY_KEYWORDS = ["hour ago", "hours ago"]


def load_previous_links():
    """Load links from previous run."""
    if PREVIOUS_LINKS_FILE.exists():
        with open(PREVIOUS_LINKS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_links_to_file(all_links):
    """Save all links to JSON file and compare with previous."""
    DATA_DIR.mkdir(exist_ok=True)

    # Load previous links for comparison
    previous_links = load_previous_links()

    # Flatten today's links to compare
    today_flat = set()
    for category_links in all_links.values():
        today_flat.update(category_links)

    previous_flat = set()
    for category_links in previous_links.values():
        previous_flat.update(category_links)

    # Calculate new and removed articles
    new_articles = today_flat - previous_flat
    removed_articles = previous_flat - today_flat

    # Save today's links atomically and persist metadata
    atomic_write(TODAY_LINKS_FILE, all_links)
    atomic_write(PREVIOUS_LINKS_FILE, all_links)
    meta = {
        "saved_at": time.time(),
        "saved_at_iso": datetime.now().isoformat(),
        "total_links": len(today_flat),
    }
    atomic_write(LINKS_META_FILE, meta)

    # Print comparison results
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"Scrape completed at {timestamp}")
    print(f"{'='*60}")
    print(f"Total articles found: {len(today_flat)}")
    print(f"New articles: {len(new_articles)}")
    print(f"Removed articles: {len(removed_articles)}")

    if new_articles:
        print(f"\n[NEW] New Articles:")
        for article in sorted(new_articles):
            print(f"  - {article}")

    if removed_articles:
        print(f"\n[REMOVED] Removed Articles:")
        for article in sorted(removed_articles):
            print(f"  - {article}")

    print(f"\n[OK] Links saved to {TODAY_LINKS_FILE}")
    print(f"{'='*60}\n")

    return {
        "timestamp": timestamp,
        "total_articles": len(today_flat),
        "new_articles": len(new_articles),
        "removed_articles": len(removed_articles),
        "new_links": sorted(list(new_articles)),
        "removed_links": sorted(list(removed_articles)),
    }


async def fetch_category_articles(category_name, url, pagination_selector):
    links = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # --- Top 5 articles ---
        await page.wait_for_selector(TOP_ARTICLES_SELECTOR)
        top_container = await page.query_selector(TOP_ARTICLES_SELECTOR)
        top_links = await top_container.query_selector_all(".td-module-thumb a")
        for link in top_links:
            # Check the article's time like we do for paginated articles
            article = await link.evaluate_handle(
                "el => el.closest('.td_module_flex')"
            )
            if not article:
                continue
            time_el = await article.query_selector("time.entry-date")
            if not time_el:
                continue
            time_text = (await time_el.inner_text()).lower()

            if any(keyword in time_text for keyword in TODAY_KEYWORDS):
                href = await link.get_attribute("href")
                links.append(href)
                print(f"[{category_name}][TOP] {href}")

        # --- Paginated articles ---
        while True:
            await page.wait_for_selector(pagination_selector)
            container = await page.query_selector(pagination_selector)
            links_on_page = await container.query_selector_all(".td-module-thumb a")
            any_today = False

            for link in links_on_page:
                # get parent article for time
                article = await link.evaluate_handle(
                    "el => el.closest('.td_module_flex')"
                )
                time_el = await article.query_selector("time.entry-date")
                if not time_el:
                    continue
                time_text = (await time_el.inner_text()).lower()

                if any(keyword in time_text for keyword in TODAY_KEYWORDS):
                    href = await link.get_attribute("href")
                    links.append(href)
                    print(f"[{category_name}] {href}")
                    any_today = True

            if not any_today:
                break  # stop if no today's articles

            # Click next page
            next_button = await page.query_selector(
                f"#next-page-{pagination_selector[1:]}"
            )
            if next_button:
                # Use JavaScript click to ensure JS handler fires
                await next_button.evaluate("el => el.click()")
                await page.wait_for_selector(
                    f"{pagination_selector} .td-module-thumb a"
                )  # wait for new articles to appear
                await page.wait_for_timeout(
                    1000
                )  # optional: extra wait for smooth loading
            else:
                break

        await browser.close()

    return links


async def main(categories=None):
    """
    Scrape articles for specified categories or all if not specified.
    
    Args:
        categories: list of category names to scrape, or None for all
    """
    if categories is None:
        categories_to_scrape = CATEGORIES
    else:
        categories_to_scrape = {k: v for k, v in CATEGORIES.items() if k in categories}
    
    all_links = {}
    total_categories = len(categories_to_scrape)
    
    for idx, (category, info) in enumerate(categories_to_scrape.items(), 1):
        print(f"\n[{idx}/{total_categories}] Fetching articles for {category}...")
        all_links[category] = await fetch_category_articles(
            category, info["url"], info["pagination_tdi"]
        )

    # Save and compare
    comparison = save_links_to_file(all_links)
    return comparison


if __name__ == "__main__":
    import sys
    
    categories = None
    if len(sys.argv) > 1:
        # Support: python scrape_links.py national,business
        categories = sys.argv[1].split(",")
        categories = [c.strip() for c in categories if c.strip()]
        invalid = [c for c in categories if c not in CATEGORIES]
        if invalid:
            print(f"Invalid categories: {invalid}")
            print(f"Available: {', '.join(CATEGORIES.keys())}")
            sys.exit(1)
    
    asyncio.run(main(categories=categories))
