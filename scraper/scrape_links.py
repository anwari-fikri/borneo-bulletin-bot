import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Map categories to their pagination container IDs
CATEGORIES = {
    "national": {
        "url": "https://borneobulletin.com.bn/category/national/",
        "pagination_tdi": "#tdi_106"
    },
    "southeast": {
        "url": "https://borneobulletin.com.bn/category/southeast/",
        "pagination_tdi": "#tdi_107"
    },
    "world": {
        "url": "https://borneobulletin.com.bn/category/world/",
        "pagination_tdi": "#tdi_106"
    },
    "business": {
        "url": "https://borneobulletin.com.bn/category/business/",
        "pagination_tdi": "#tdi_107"
    },
    # Add more categories here
}

DATA_DIR = Path(__file__).parent.parent / "data"
TODAY_LINKS_FILE = DATA_DIR / "today_links.json"
PREVIOUS_LINKS_FILE = DATA_DIR / "previous_links.json"

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
    
    # Save today's links as the new previous for next run
    if PREVIOUS_LINKS_FILE.exists():
        os.remove(PREVIOUS_LINKS_FILE)
    with open(TODAY_LINKS_FILE, "w") as f:
        json.dump(all_links, f, indent=2)
    with open(PREVIOUS_LINKS_FILE, "w") as f:
        json.dump(all_links, f, indent=2)
    
    # Print comparison results
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"Scrape completed at {timestamp}")
    print(f"{'='*60}")
    print(f"Total articles found: {len(today_flat)}")
    print(f"New articles: {len(new_articles)}")
    print(f"Removed articles: {len(removed_articles)}")
    
    if new_articles:
        print(f"\n🆕 New Articles:")
        for article in sorted(new_articles):
            print(f"  - {article}")
    
    if removed_articles:
        print(f"\n❌ Removed Articles:")
        for article in sorted(removed_articles):
            print(f"  - {article}")
    
    print(f"\n✅ Links saved to {TODAY_LINKS_FILE}")
    print(f"{'='*60}\n")
    
    return {
        "timestamp": timestamp,
        "total_articles": len(today_flat),
        "new_articles": len(new_articles),
        "removed_articles": len(removed_articles),
        "new_links": sorted(list(new_articles)),
        "removed_links": sorted(list(removed_articles))
    }

async def fetch_category_articles(category_name, url, pagination_selector):
    links = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)

        # --- Top 5 articles ---
        await page.wait_for_selector(TOP_ARTICLES_SELECTOR)
        top_container = await page.query_selector(TOP_ARTICLES_SELECTOR)
        top_links = await top_container.query_selector_all(".td-module-thumb a")
        for link in top_links:
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
                article = await link.evaluate_handle("el => el.closest('.td_module_flex')")
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
            next_button = await page.query_selector(f"#next-page-{pagination_selector[1:]}")
            if next_button:
                # Use JavaScript click to ensure JS handler fires
                await next_button.evaluate("el => el.click()")
                await page.wait_for_selector(f"{pagination_selector} .td-module-thumb a")  # wait for new articles to appear
                await page.wait_for_timeout(1000)  # optional: extra wait for smooth loading
            else:
                break

        await browser.close()
    
    return links

async def main():
    all_links = {}
    for category, info in CATEGORIES.items():
        print(f"Fetching articles for {category}...")
        all_links[category] = await fetch_category_articles(category, info["url"], info["pagination_tdi"])
    
    # Save and compare
    comparison = save_links_to_file(all_links)
    return comparison

if __name__ == "__main__":
    asyncio.run(main())
