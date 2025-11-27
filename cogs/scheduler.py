"""
Scheduler cog: /toggle_scheduled_news and background task for 9 AM GMT+8 posts.
"""
import discord
from discord.ext import commands, tasks
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("scheduler_cog")

SCHEDULE_STATE_FILE = Path(__file__).parent.parent / "data" / "schedule_state.json"


class SchedulerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.schedule_state = self._load_schedule_state()
        self.daily_news_task.start()

    def _load_schedule_state(self):
        """Load schedule_state.json from disk."""
        if SCHEDULE_STATE_FILE.exists():
            try:
                with open(SCHEDULE_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load schedule_state.json: %s", e)
        return {}

    def _save_schedule_state(self):
        """Save schedule_state.json to disk."""
        try:
            SCHEDULE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULE_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.schedule_state, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save schedule_state.json: %s", e)

    @commands.hybrid_command(name="toggle_scheduled_news", description="Toggle scheduled news for a category or all.")
    @discord.app_commands.describe(category="Category to toggle or 'all' for all categories")
    async def toggle_scheduled_news(self, ctx, category: str = "all"):
        scraper = self.bot.get_cog("ScraperCog")
        if not scraper:
            await ctx.send("❌ Scraper cog not loaded.")
            return

        guild_id = str(ctx.guild.id) if ctx.guild else "default"
        channel_id = str(ctx.channel.id)

        if guild_id not in self.schedule_state:
            self.schedule_state[guild_id] = {}

        if guild_id not in self.schedule_state or "channels" not in self.schedule_state[guild_id]:
            self.schedule_state[guild_id] = {"channels": {}}

        if channel_id not in self.schedule_state[guild_id]["channels"]:
            self.schedule_state[guild_id]["channels"][channel_id] = {}

        channel_config = self.schedule_state[guild_id]["channels"][channel_id]

        if category.lower() == "all":
            available = scraper.get_categories()
            for cat in available:
                channel_config[cat] = not channel_config.get(cat, False)
            self._save_schedule_state()
            enabled = [cat for cat, enabled in channel_config.items() if enabled]
            await ctx.send(f"✅ Scheduled news toggled for all categories.\n**Enabled:** {', '.join(enabled) if enabled else 'None'}")
        else:
            available = scraper.get_categories()
            if category.lower() not in [c.lower() for c in available]:
                await ctx.send(f"❌ Category '{category}' not found.")
                return
            channel_config[category] = not channel_config.get(category, False)
            self._save_schedule_state()
            status = "✅ Enabled" if channel_config[category] else "❌ Disabled"
            await ctx.send(f"{status} scheduled news for '{category}'.")

    @tasks.loop(minutes=1)
    async def daily_news_task(self):
        """Check every minute if it's 9 AM GMT+8, then post to subscribed channels."""
        # Get current time in GMT+8
        gmt_8 = timezone(timedelta(hours=8))
        now = datetime.now(gmt_8)

        # Check if it's exactly 9 AM (minute = 0, hour = 9)
        if now.hour == 9 and now.minute == 0:
            logger.info("Running scheduled news task at 9 AM GMT+8...")
            await self._post_scheduled_news()

    async def _post_scheduled_news(self):
        """Post scheduled news to all subscribed channels."""
        scraper = self.bot.get_cog("ScraperCog")
        if not scraper:
            logger.warning("Scraper cog not loaded; skipping scheduled news.")
            return

        # Trigger scrape
        success = await scraper.run_scraper(force=False)
        if not success:
            logger.warning("Scraper failed during scheduled task.")
            return

        for guild_id, guild_config in self.schedule_state.items():
            for channel_id_str, channel_config in guild_config.get("channels", {}).items():
                try:
                    channel_id = int(channel_id_str)
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        logger.warning("Channel %d not found.", channel_id)
                        continue

                    enabled_categories = [cat for cat, enabled in channel_config.items() if enabled]
                    if not enabled_categories:
                        continue

                    for category in enabled_categories:
                        articles = scraper.get_articles_for_category(category)
                        today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]

                        if today_articles:
                            # Post top 5
                            embed = discord.Embed(
                                title=f"📰 {category.capitalize()} - Today's News",
                                color=discord.Color.blue(),
                            )
                            for i, article in enumerate(today_articles[:5], 1):
                                title = article.get("title", "No title")[:256]
                                url = article.get("url", "")
                                embed.add_field(
                                    name=f"{i}. {title}",
                                    value=f"[Read more]({url})" if url else "No URL",
                                    inline=False,
                                )
                            await channel.send(embed=embed)
                except Exception as e:
                    logger.exception("Error posting scheduled news to channel %s: %s", channel_id_str, e)

    @daily_news_task.before_loop
    async def before_daily_news_task(self):
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(SchedulerCog(bot))
