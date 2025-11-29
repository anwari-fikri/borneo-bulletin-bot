"""
Subscription cog: /subscribe, /unsubscribe, /subscriptions commands.
Stores user subscriptions in memory and optionally persists to JSON.
"""
import discord
from discord.ext import commands
import json
import logging
from pathlib import Path

logger = logging.getLogger("subscription_cog")

SUBSCRIPTIONS_FILE = Path(__file__).parent.parent / "data" / "user_subscriptions.json"


class SubscriptionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # user_id -> set of categories
        self.subscriptions = self._load_subscriptions()

    def _load_subscriptions(self):
        """Load user subscriptions from JSON if exists."""
        if SUBSCRIPTIONS_FILE.exists():
            try:
                with open(SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert lists back to sets
                    return {user_id: set(cats) for user_id, cats in data.items()}
            except Exception as e:
                logger.warning("Failed to load subscriptions: %s", e)
        return {}

    def _save_subscriptions(self):
        """Save subscriptions to JSON."""
        try:
            SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Convert sets to lists for JSON serialization
            data = {user_id: list(cats) for user_id, cats in self.subscriptions.items()}
            with open(SUBSCRIPTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save subscriptions: %s", e)

    @commands.hybrid_command(name="subscribe", description="Subscribe to news updates for a category or 'all'.")
    @discord.app_commands.describe(category="Category to subscribe to (e.g., 'national') or 'all' for all categories")
    async def subscribe(self, ctx, category: str):
        scraper = self.bot.get_cog("ScraperCog")
        if not scraper:
            await ctx.send("❌ Scraper cog not loaded.")
            return

        available = scraper.get_categories()
        user_id = str(ctx.author.id)
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()

        if category.lower() == "all":
            # Subscribe to all categories
            already_subscribed = self.subscriptions[user_id].copy()
            self.subscriptions[user_id].update(available)
            self._save_subscriptions()
            new_subs = self.subscriptions[user_id] - already_subscribed
            if new_subs:
                await ctx.send(f"✅ Subscribed to all categories ({len(self.subscriptions[user_id])} total).")
            else:
                await ctx.send(f"ℹ️ Already subscribed to all {len(available)} categories.")
        else:
            if category.lower() not in [c.lower() for c in available]:
                await ctx.send(f"❌ Category '{category}' not found. Available: {', '.join(available)}")
                return

            if category in self.subscriptions[user_id]:
                await ctx.send(f"ℹ️ You are already subscribed to '{category}'.")
            else:
                self.subscriptions[user_id].add(category)
                self._save_subscriptions()
                await ctx.send(f"✅ Subscribed to '{category}'. You now have {len(self.subscriptions[user_id])} subscriptions.")

    @commands.hybrid_command(name="unsubscribe", description="Unsubscribe from news updates for a category.")
    @discord.app_commands.describe(category="Category to unsubscribe from")
    async def unsubscribe(self, ctx, category: str):
        user_id = str(ctx.author.id)
        if user_id not in self.subscriptions or category not in self.subscriptions[user_id]:
            await ctx.send(f"ℹ️ You are not subscribed to '{category}'.")
            return

        self.subscriptions[user_id].discard(category)
        self._save_subscriptions()
        
        # Auto-disable toggle if subscriptions become empty
        scheduler = self.bot.get_cog("SchedulerCog")
        if scheduler and not self.subscriptions[user_id]:
            guild_id = str(ctx.guild.id) if ctx.guild else "default"
            channel_id = str(ctx.channel.id)
            if guild_id in scheduler.schedule_state and "channels" in scheduler.schedule_state[guild_id]:
                if channel_id in scheduler.schedule_state[guild_id]["channels"]:
                    scheduler.schedule_state[guild_id]["channels"][channel_id] = {}
                    scheduler._save_schedule_state()
        
        await ctx.send(f"✅ Unsubscribed from '{category}'. You now have {len(self.subscriptions[user_id])} subscriptions.")

    @commands.hybrid_command(name="subscriptions", description="Show your current category subscriptions.")
    async def subscriptions(self, ctx):
        user_id = str(ctx.author.id)
        if user_id not in self.subscriptions or not self.subscriptions[user_id]:
            await ctx.send("ℹ️ You are not subscribed to any categories.")
            return

        subs = sorted(list(self.subscriptions[user_id]))
        embed = discord.Embed(title="📌 Your Subscriptions", color=discord.Color.teal())
        embed.description = "\n".join([f"• {cat}" for cat in subs])
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SubscriptionCog(bot))
