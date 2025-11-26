import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

DATA_DIR = Path(__file__).parent.parent / "data"
TODAY_LINKS_FILE = DATA_DIR / "today_links.json"
ARTICLES_FILE = DATA_DIR / "articles.json"

async def fetch_article_title(url):
    """Fetch article details including title, date, content, and featured image."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=15000)
            
            await page.wait_for_selector(".tdb-title-text", timeout=5000)
            
            """Title and Date"""
            title = await page.query_selector(".tdb-title-text")
            title_text = await title.inner_text()
            date = await page.query_selector("time.entry-date")
            datetime = await date.get_attribute("datetime") if date else "Unknown date"
            
            """Content"""
            contents_container = await page.query_selector(".vc_column_inner.tdi_84")
            context_text = await contents_container.query_selector_all("p")
            content_text = "\n".join([await p.inner_text() for p in context_text])
            
            """Featured Image"""
            featured_image_url = None
            featured_caption = None
            featured_image_container = await page.query_selector(".vc_column_inner.tdi_84")
            if featured_image_container:
                featured_image = await featured_image_container.query_selector("img")
                featured_caption_el = await featured_image_container.query_selector("figcaption")
                if featured_image:
                    featured_image_url = await featured_image.get_attribute("src")
                if featured_caption_el:
                    featured_caption = await featured_caption_el.inner_text()
            
            await browser.close()
            
            return {
                "title": title_text.strip(),
                "date": datetime,
                "content": content_text,
                "featured_image": featured_image_url,
                "featured_caption": featured_caption
            }
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None

def load_cached_articles():
    """Load previously scraped articles from cache."""
    if ARTICLES_FILE.exists():
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_cached_url_titles(articles):
    """Extract all cached URLs for quick lookup."""
    cached = set()
    for category_articles in articles.values():
        for article in category_articles:
            cached.add(article["url"])
    return cached

async def scrape_all_articles(force_rescrape=False):
    """Scrape titles from all links in today_links.json and save to articles.json."""
    
    # Load links from today_links.json
    if not TODAY_LINKS_FILE.exists():
        print(f"❌ File not found: {TODAY_LINKS_FILE}")
        print("Run scrape_links.py first to generate today_links.json")
        return
    
    with open(TODAY_LINKS_FILE, "r") as f:
        today_links = json.load(f)
    
    # Load cached articles
    cached_articles = load_cached_articles()
    cached_urls = get_cached_url_titles(cached_articles)
    
    # Flatten all links with category info
    all_tasks = []
    for category, links in today_links.items():
        for link in links:
            all_tasks.append((category, link))
    
    total_links = len(all_tasks)
    
    if force_rescrape:
        print(f"🔄 Force re-scraping all {total_links} articles (ignoring cache)...\n")
        to_scrape = all_tasks
        skipped_count = 0
    else:
        # Separate links that need scraping from cached ones
        to_scrape = []
        skipped_count = 0
        
        for category, link in all_tasks:
            if link not in cached_urls:
                to_scrape.append((category, link))
            else:
                skipped_count += 1
        
        if skipped_count > 0:
            print(f"📄 Found {skipped_count} cached articles. Scraping {len(to_scrape)} new articles...\n")
        else:
            print(f"📄 Starting to scrape {len(to_scrape)} articles in parallel...\n")
    
    if len(to_scrape) == 0:
        print("✅ All articles already cached! No new articles to scrape.")
        print(f"Use --force to re-scrape all articles.\n")
        return
    
    # Scrape all articles concurrently with a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
    
    async def scrape_with_semaphore(category, link, index):
        async with semaphore:
            print(f"  [{index + 1}/{len(to_scrape)}] Fetching: {link}")
            article_data = await fetch_article_title(link)
            if article_data:
                print(f"    ✅ {article_data['title']}")
                return (category, link, article_data)
            else:
                print(f"    ⚠️  Could not fetch article")
                return None
    
    # Run all tasks in parallel
    tasks = [scrape_with_semaphore(category, link, i) for i, (category, link) in enumerate(to_scrape)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Start with cached articles or initialize fresh
    articles = cached_articles if not force_rescrape else {}
    
    # Initialize categories if not present
    for category in today_links.keys():
        if category not in articles:
            articles[category] = []
    
    # Add newly scraped results
    for result in results:
        if result and not isinstance(result, Exception):
            category, link, article_data = result
            # Remove old entry if re-scraping
            if force_rescrape:
                articles[category] = [a for a in articles[category] if a["url"] != link]
            articles[category].append({
                "url": link,
                "title": article_data["title"],
                "date": article_data["date"],
                "content": article_data["content"],
                "featured_image": article_data["featured_image"],
                "featured_caption": article_data["featured_caption"]
            })
    
    # Save to articles.json
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    # Print summary
    total_scraped = sum(len(articles_in_category) for articles_in_category in articles.values())
    newly_scraped = len([r for r in results if r and not isinstance(r, Exception)])
    print(f"\n{'='*60}")
    print(f"✅ Scraping completed!")
    print(f"Newly scraped: {newly_scraped}")
    print(f"Cached articles: {skipped_count if not force_rescrape else 0}")
    print(f"Total articles: {total_scraped}")
    print(f"Saved to: {ARTICLES_FILE}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    force_rescrape = "--force" in sys.argv
    asyncio.run(scrape_all_articles(force_rescrape=force_rescrape))