"""
News cog: /get_todays_news, /latest, /categories commands.
Includes pagination for large result sets.
"""
import discord
from discord.ext import commands
from discord import ui
import logging
from datetime import datetime
import os
from urllib.parse import quote_plus
import io
import hashlib
import mimetypes
import aiohttp
import uuid
import time

logger = logging.getLogger("news_cog")


class NewsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # small in-memory cache for digest state (short-lived)
        self._digest_cache = {}

    async def get_scraper_cog(self):
        """Get the scraper cog instance."""
        return self.bot.get_cog("ScraperCog")



    def _build_digest_embed(self, articles, category):
        """Build a compact digest embed with all today's articles (title + short desc)."""
        embed = discord.Embed(
            title=f"📰 {category.capitalize()} - Today's News",
            color=discord.Color.blue(),
        )
        for i, article in enumerate(articles, 1):
            title = article.get("title", "No title")[:256]
            url = article.get("url", "")
            short = article.get("excerpt", "") or (article.get("content", "") or "")[:100]
            embed.add_field(name=f"{i}. {title}", value=(f"{short}\n[Link]({url})" if url else short), inline=False)

        # thumbnail: use first article image if available
        first_image = articles[0].get("featured_image") if articles else None
        proxy_base = os.getenv("IMAGE_PROXY_BASE")
        if first_image:
            if proxy_base:
                embed.set_thumbnail(url=proxy_base.rstrip("/") + "/image?url=" + quote_plus(first_image))
            else:
                embed.set_thumbnail(url=first_image)

        embed.set_footer(text=f"📖 Use `/read_full {category}` to read full articles in a thread • {len(articles)} articles today")
        return embed

    async def send_digest(self, channel, category, articles):
        """Send a compact digest message to `channel` with interactive view."""
        if not articles:
            return None

        digest_id = str(uuid.uuid4())
        embed = self._build_digest_embed(articles, category)
        view = DigestView(self, digest_id, articles, category)
        # cache articles briefly for the view lifetime
        self._digest_cache[digest_id] = {"articles": articles, "ts": time.time()}
        try:
            msg = await channel.send(embed=embed, view=view)
        except Exception:
            # fallback: send without view
            msg = await channel.send(embed=embed)
        return msg

    async def _scrape_and_get_articles(self, ctx, scraper, category):
        """Scrape a category and return today's articles, or None if scrape failed."""
        status_msg = await ctx.send(f"🔄 No cached articles for today. Scraping **{category}**...\n_(This may take 30-60 seconds)_")
        
        async def update_progress(message):
            try:
                if "[SCRAPER]" in message or "Step" in message or "completed" in message.lower():
                    await status_msg.edit(content=f"🔄 Scraping **{category}**...\n```\n{message}\n```")
            except:
                pass
        
        success = await scraper.run_scraper(force=False, categories=[category], progress_callback=update_progress)
        if not success:
            await status_msg.edit(content="❌ Scraping failed. Try again later.")
            return None
        
        articles = scraper.get_articles_for_category(category)
        today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]
        
        if today_articles:
            await status_msg.edit(content="✅ Scraping complete!")
            return today_articles
        else:
            await status_msg.edit(content="❌ No articles found after scraping.")
            return None

    async def _post_articles_to_thread(self, thread, category, articles):
        """Post article digests to a thread."""
        await thread.send(f"Reading **{len(articles)}** articles from {category.capitalize()} today...")
        for i, article in enumerate(articles, 1):
            title = article.get("title", "No title")[:256]
            url = article.get("url", "")
            content = article.get("content", "") or ""
            description = content[:4096]
            
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
                color=discord.Color.blue(),
                url=url
            )
            embed.set_footer(text=f"{date_text} • Article {i}/{len(articles)}")
            
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
                                ext = mimetypes.guess_extension(ctype.split(";")[0].strip()) or ".jpg"
                                fname = hashlib.sha1(image.encode("utf-8")).hexdigest() + ext
                                file_obj = discord.File(io.BytesIO(img_bytes), filename=fname)
                                embed.set_image(url=f"attachment://{fname}")
                                await thread.send(embed=embed, file=file_obj)
                                attached = True
                except Exception as e:
                    logger.debug("Could not download image for article %d: %s", i, e)

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
                    logger.warning("Failed to set proxied image for article %d: %s", i, e)

            # Add caption if available
            caption = article.get("featured_caption", "")
            if caption:
                embed.add_field(name="Caption", value=caption[:1024], inline=True)

    @commands.hybrid_command(name="read_full", description="Read full articles for today in a threaded discussion.")
    @discord.app_commands.describe(category="Article category (e.g., 'national')")
    async def read_full(self, ctx, category: str = None):
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
            await ctx.send(f"📚 Available categories: {', '.join(cats)}\nUsage: `/read_full [category]`")
            return

        # Check if category exists
        available = scraper.get_categories()
        if category.lower() not in [c.lower() for c in available]:
            await ctx.send(f"❌ Category '{category}' not found. Available: {', '.join(available)}")
            return

        # Create thread first (upfront)
        thread = None
        try:
            starter = await ctx.send(f"📖 Starting thread for **{category.capitalize()}** — preparing articles...")
            thread = await starter.create_thread(name=f"📖 {category.capitalize()} - Full Articles")
        except Exception as e:
            logger.debug("Thread creation failed: %s", e)
            await ctx.send(f"🔖 Could not create a thread (missing permissions?). Posting full articles in this channel instead.")
            thread = ctx.channel

        # Get articles for category
        articles = scraper.get_articles_for_category(category)
        today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]

        # If no articles, scrape and retry
        if not today_articles:
            today_articles = await self._scrape_and_get_articles(ctx, scraper, category)
            if not today_articles:
                return

        # Post articles to thread
        await self._post_articles_to_thread(thread, category, today_articles)

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

    @commands.hybrid_command(name="send_digest", description="Send digest(s) to this channel. If no category provided, send all subscribed categories.")
    @discord.app_commands.describe(category="Article category (e.g., 'national') or leave empty for all subscribed")
    async def send_digest_cmd(self, ctx, category: str = None):
        """Manually send digest(s) to the current channel."""
        scraper = await self.get_scraper_cog()
        if not scraper:
            await ctx.send("❌ Scraper cog not loaded.")
            return

        available = scraper.get_categories()
        
        # If no category provided, use user's subscriptions
        if not category:
            subscription_cog = self.bot.get_cog("SubscriptionCog")
            if not subscription_cog:
                await ctx.send("❌ Subscription cog not loaded.")
                return
            
            user_id = str(ctx.author.id)
            if user_id not in subscription_cog.subscriptions or not subscription_cog.subscriptions[user_id]:
                await ctx.send(f"ℹ️ You have no subscriptions. Use `/subscribe [category]` or `/subscribe all` first.")
                return
            
            categories_to_send = sorted(list(subscription_cog.subscriptions[user_id]))
        else:
            # Single category provided
            if category.lower() not in [c.lower() for c in available]:
                await ctx.send(f"❌ Category '{category}' not found. Available: {', '.join(available)}")
                return
            categories_to_send = [category]

        # Prepare categories that need scraping (no cached articles)
        need_scrape = []
        for cat in categories_to_send:
            articles = scraper.get_articles_for_category(cat)
            today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]
            if not today_articles:
                need_scrape.append(cat)
        
        # Scrape all categories that need it
        if need_scrape:
            await ctx.send(f"🔄 Scraping {len(need_scrape)} category/categories...")
            success = await scraper.run_scraper(force=False, categories=need_scrape)
            if not success:
                await ctx.send("❌ Scraping failed.")
                return
        
        # Send digests for all categories
        sent_count = 0
        for cat in categories_to_send:
            articles = scraper.get_articles_for_category(cat)
            today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]
            
            if today_articles:
                msg = await self.send_digest(ctx.channel, cat, today_articles)
                if msg:
                    sent_count += 1
        
        if sent_count > 0:
            await ctx.send(f"✅ Sent {sent_count} digest(s)!", delete_after=5)
        else:
            await ctx.send(f"❌ No articles found for the requested categor{'ies' if len(categories_to_send) > 1 else 'y'}.")


class DigestView(ui.View):
    def __init__(self, cog: NewsCog, digest_id: str, articles, category, timeout=900):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.digest_id = digest_id
        self.articles = articles
        self.category = category

async def setup(bot):
    await bot.add_cog(NewsCog(bot))
