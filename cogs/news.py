"""
News cog: /get_todays_news, /latest, /categories commands.
Includes pagination for large result sets.
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime
import os
from urllib.parse import quote_plus
import io
import hashlib
import mimetypes
import aiohttp

logger = logging.getLogger("news_cog")


class NewsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_scraper_cog(self):
        """Get the scraper cog instance."""
        return self.bot.get_cog("ScraperCog")

    async def _send_paginated_news(self, ctx, category, articles, title_suffix="Today's News", color=discord.Color.blue()):
        """Send each article as its own embed with featured image."""
        if not articles:
            await ctx.send("❌ No articles to display.")
            return
        
        total = len(articles)
        for idx, article in enumerate(articles, 1):
            # Title
            title = article.get("title", "No title")[:256]

            # Content: take first paragraph (split on newline), fallback to whole content
            raw_content = article.get("content", "") or ""
            first_par = ""
            for part in raw_content.split("\n"):
                p = part.strip()
                if p:
                    first_par = p
                    break
            if not first_par:
                first_par = raw_content.strip()
            # cap description to safe size for embeds (first paragraph)
            description = first_par[:512]

            # Prepare date text for footer so it's available before any sends
            date_raw = article.get("date", "Unknown date")
            date_text = date_raw
            try:
                dt = datetime.fromisoformat(date_raw)
                date_text = dt.strftime("%d/%m/%Y")
            except Exception:
                pass

            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                url=article.get("url", "")
            )
            embed.set_footer(text=f"{date_text} • Article {idx}/{total}")

            # Add featured image - try to attach image bytes so Discord will always show it.
            image = article.get("featured_image")
            attached = False
            if image and isinstance(image, str) and image.strip():
                # First try: download image and send as attachment (attachment://filename)
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image, headers={"User-Agent": "Mozilla/5.0"}, timeout=20) as resp:
                            if resp.status == 200:
                                img_bytes = await resp.read()
                                ctype = resp.headers.get("Content-Type", "application/octet-stream")
                                ext = mimetypes.guess_extension(ctype.split(";")[0].strip() ) or ".jpg"
                                fname = hashlib.sha1(image.encode("utf-8")).hexdigest() + ext
                                file_obj = discord.File(io.BytesIO(img_bytes), filename=fname)
                                embed.set_image(url=f"attachment://{fname}")
                                await ctx.send(embed=embed, file=file_obj)
                                attached = True
                except Exception as e:
                    logger.debug("Could not download image for article %d: %s", idx, e)

            if attached:
                # already sent with attachment
                continue

            # Fallback: if proxy is configured, use proxy URL so Discord can fetch it
            proxy_base = os.getenv("IMAGE_PROXY_BASE")
            if image and proxy_base:
                try:
                    proxied = proxy_base.rstrip("/") + "/image?url=" + quote_plus(image)
                    embed.set_image(url=proxied)
                except Exception as e:
                    logger.warning("Failed to set proxied image for article %d: %s", idx, e)

            # Add caption if available
            caption = article.get("featured_caption", "")
            if caption:
                embed.add_field(name="Caption", value=caption[:1024], inline=True)

            # footer already set earlier

            await ctx.send(embed=embed)

    @commands.hybrid_command(name="get_todays_news", description="Get today's news from a category (auto-scrapes if needed).")
    @discord.app_commands.describe(category="Article category (e.g., 'national')")
    async def get_todays_news(self, ctx, category: str = None):
        scraper = await self.get_scraper_cog()
        if not scraper:
            await ctx.send("❌ Scraper cog not loaded.")
            return

        # Show available categories if none provided
        if not category:
            cats = scraper.get_categories()
            if not cats:
                await ctx.send("❌ No categories available. Try scraping first.")
                return
            await ctx.send(f"📚 Available categories: {', '.join(cats)}\nUsage: `/get_todays_news [category]`")
            return

        # Check if category exists
        available = scraper.get_categories()
        if category.lower() not in [c.lower() for c in available]:
            await ctx.send(f"❌ Category '{category}' not found. Available: {', '.join(available)}")
            return

        # Get articles for category
        articles = scraper.get_articles_for_category(category)

        # Filter by today's date
        today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]

        if today_articles:
            # Serve from cache with pagination
            await self._send_paginated_news(ctx, category, today_articles, "Today's News")
        else:
            # No today's articles; trigger category-specific scrape with progress
            status_msg = await ctx.send(f"🔄 No cached articles for today. Scraping **{category}**...\n_(This may take 30-60 seconds)_")
            
            async def update_progress(message):
                try:
                    # Only update for key milestones
                    if "[SCRAPER]" in message or "Step" in message or "completed" in message.lower():
                        await status_msg.edit(content=f"🔄 Scraping **{category}**...\n```\n{message}\n```")
                except:
                    pass
            
            success = await scraper.run_scraper(force=False, categories=[category], progress_callback=update_progress)
            if success:
                articles = scraper.get_articles_for_category(category)
                today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]
                if today_articles:
                    await status_msg.delete()
                    await self._send_paginated_news(ctx, category, today_articles, "Today's News (Fresh)", discord.Color.green())
                else:
                    await status_msg.edit(content="❌ No articles found after scraping.")
            else:
                await status_msg.edit(content="❌ Scraping failed. Try again later.")

    @commands.hybrid_command(name="latest", description="Get the latest 1-3 articles from a category (no scrape).")
    @discord.app_commands.describe(
        category="Article category (e.g., 'national')",
        count="Number of articles (1-3, default 3)"
    )
    async def latest(self, ctx, category: str = None, count: int = 3):
        scraper = await self.get_scraper_cog()
        if not scraper:
            await ctx.send("❌ Scraper cog not loaded.")
            return

        if not category:
            cats = scraper.get_categories()
            if not cats:
                await ctx.send("❌ No categories available.")
                return
            await ctx.send(f"📚 Available categories: {', '.join(cats)}\nUsage: `/latest [category] [count]`")
            return

        available = scraper.get_categories()
        if category.lower() not in [c.lower() for c in available]:
            await ctx.send(f"❌ Category '{category}' not found.")
            return

        count = max(1, min(count, 3))  # Clamp to 1-3
        articles = scraper.get_articles_for_category(category)
        latest_articles = articles[-count:] if articles else []

        if latest_articles:
            embed = discord.Embed(title=f"📰 Latest {count} - {category.capitalize()}", color=discord.Color.gold())
            for i, article in enumerate(reversed(latest_articles), 1):
                title = article.get("title", "No title")[:256]
                url = article.get("url", "")
                embed.add_field(name=f"{i}. {title}", value=f"[Read more]({url})" if url else "No URL", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No articles in that category.")

    @commands.hybrid_command(name="categories", description="List all available article categories.")
    async def categories(self, ctx):
        scraper = await self.get_scraper_cog()
        if not scraper:
            await ctx.send("❌ Scraper cog not loaded.")
            return

        cats = scraper.get_categories()
        if cats:
            embed = discord.Embed(title="📚 Available Categories", color=discord.Color.purple())
            embed.description = "\n".join([f"• {c}" for c in cats])
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ No categories available. Try scraping first.")


async def setup(bot):
    await bot.add_cog(NewsCog(bot))
