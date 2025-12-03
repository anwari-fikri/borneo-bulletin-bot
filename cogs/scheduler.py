"""
Scheduler cog: /toggle_scheduled_news and background task for 9 AM GMT+8 posts.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import random
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

    @commands.hybrid_command(name="toggle_scheduled_news", description="Turn scheduled news ON or OFF.")
    @discord.app_commands.describe(state="'on' to enable scheduled news or 'off' to disable")
    async def toggle_scheduled_news(self, ctx, state: str = None):
        scraper = self.bot.get_cog("ScraperCog")
        subscription = self.bot.get_cog("SubscriptionCog")
        if not scraper or not subscription:
            await ctx.send("❌ Required cogs not loaded.")
            return

        guild_id = str(ctx.guild.id) if ctx.guild else "default"
        channel_id = str(ctx.channel.id)

        if guild_id not in self.schedule_state:
            self.schedule_state[guild_id] = {"channels": {}}
        if "channels" not in self.schedule_state[guild_id]:
            self.schedule_state[guild_id]["channels"] = {}
        if channel_id not in self.schedule_state[guild_id]["channels"]:
            self.schedule_state[guild_id]["channels"][channel_id] = {}

        channel_config = self.schedule_state[guild_id]["channels"][channel_id]

        if state is None or state.lower() not in ["on", "off"]:
            enabled = [cat for cat, enabled in channel_config.items() if enabled]
            status = "✅ ON" if enabled else "❌ OFF"
            msg = f"Scheduled news status: {status}\n"
            if enabled:
                msg += f"**Enabled categories:** {', '.join(enabled)}"
            else:
                msg += "Use `/toggle_scheduled_news on` to enable."
            await ctx.send(msg)
            return

        if state.lower() == "on":
            # Check if user has subscriptions
            user_id = str(ctx.author.id)
            if user_id not in subscription.subscriptions or not subscription.subscriptions[user_id]:
                available = scraper.get_categories()
                embed = discord.Embed(
                    title="📌 No Subscriptions",
                    description="You must subscribe to at least 1 category before enabling scheduled news.",
                    color=discord.Color.orange(),
                )
                embed.add_field(
                    name="Available Categories",
                    value="\n".join([f"• {cat}" for cat in available]),
                    inline=False,
                )
                embed.set_footer(text="Use `/subscribe [category]` or `/subscribe all` to subscribe.")
                await ctx.send(embed=embed)
                return

            # Enable all subscribed categories
            user_subs = subscription.subscriptions[user_id]
            for cat in user_subs:
                channel_config[cat] = True
            self._save_schedule_state()
            await ctx.send(f"✅ Scheduled news enabled for {len(user_subs)} subscribed categories.")
        else:  # state.lower() == "off"
            # Disable all categories
            channel_config.clear()
            self._save_schedule_state()
            await ctx.send("❌ Scheduled news disabled.")

    @tasks.loop(minutes=1)
    async def daily_news_task(self):
        """Check every minute if it's 9 AM GMT+8, then post to subscribed channels."""
        # Get current time in GMT+8
        gmt_8 = timezone(timedelta(hours=8))
        now = datetime.now(gmt_8)

        # Check if it's exactly 9 AM (minute = 0, hour = 9)
        if now.hour == 9 and now.minute == 00:
            logger.info("Running scheduled news task at 9 AM GMT+8...")
            await self._post_scheduled_news()

    async def _post_scheduled_news(self):
        """Post scheduled news digests to all subscribed channels (categories they toggled ON)."""
        scraper = self.bot.get_cog("ScraperCog")
        news_cog = self.bot.get_cog("NewsCog")
        if not scraper:
            logger.warning("Scraper cog not loaded; skipping scheduled news.")
            return

        # Trigger full scrape once at the start
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
                    
                    # If no categories are subscribed, send a helpful message
                    if not enabled_categories:
                        available = scraper.get_categories()
                        embed = discord.Embed(
                            title="📰 No Subscriptions Active",
                            description="This channel has no categories toggled for scheduled digests.",
                            color=discord.Color.orange(),
                        )
                        embed.add_field(
                            name="Available Categories",
                            value="\n".join([f"• {cat}" for cat in available]),
                            inline=False,
                        )
                        embed.set_footer(text="Use `/toggle_scheduled_news [category]` to enable digests.")
                        try:
                            await channel.send(embed=embed)
                        except Exception as e:
                            logger.warning("Could not send subscription reminder to channel %d: %s", channel_id, e)
                        continue

                    for category in enabled_categories:
                        articles = scraper.get_articles_for_category(category)
                        today_articles = [a for a in articles if scraper.is_today(a.get("date", ""))]

                        if today_articles:
                            # Send digest using NewsCog (if available)
                            if news_cog:
                                try:
                                    await news_cog.send_digest(channel, category, today_articles)
                                except Exception as e:
                                    logger.exception("Error sending digest to channel %d for %s: %s", channel_id, category, e)
                            else:
                                # Fallback: send plain embed
                                embed = discord.Embed(
                                    title=f"📰 {category.capitalize()} - Today's News",
                                    color=discord.Color.blue(),
                                )
                                for i, article in enumerate(today_articles, 1):
                                    title = article.get("title", "No title")[:256]
                                    url = article.get("url", "")
                                    short = article.get("excerpt", "") or (article.get("content", "") or "")[:100]
                                    embed.add_field(
                                        name=f"{i}. {title}",
                                        value=(f"{short}\n[Link]({url})" if url else short),
                                        inline=False,
                                    )
                                embed.set_footer(text=f"📖 Use `/read_full {category}` to read full articles in a thread • {len(today_articles)} articles today")
                                await channel.send(embed=embed)

                        # small jitter between sends to avoid bursts
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    logger.exception("Error posting scheduled news to channel %s: %s", channel_id_str, e)

    @daily_news_task.before_loop
    async def before_daily_news_task(self):
        """Wait until bot is ready before starting the task."""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(SchedulerCog(bot))
