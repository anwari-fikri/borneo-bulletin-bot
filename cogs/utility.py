"""
Utility cog: /ping, /help commands.
"""
import discord
from discord.ext import commands


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Check bot latency.")
    async def ping(self, ctx):
        latency = self.bot.latency
        await ctx.send(f"🏓 Pong! Latency: {latency * 1000:.2f}ms")

    @commands.hybrid_command(name="commands", description="List all available commands.")
    async def commands(self, ctx):
        embed = discord.Embed(title="📖 Borneo Bulletin Bot - Commands", color=discord.Color.blurple())

        embed.add_field(
            name="📰 News Commands",
            value=(
                "`/get_todays_news [category]` - Get today's news (auto-scrape if needed)\n"
                "`/latest [category] [count]` - Get latest 1-3 articles (no scrape)\n"
                "`/categories` - List all available categories"
            ),
            inline=False,
        )

        embed.add_field(
            name="📌 Subscription Commands",
            value=(
                "`/subscribe [category]` - Subscribe to a category\n"
                "`/unsubscribe [category]` - Unsubscribe from a category\n"
                "`/subscriptions` - Show your subscriptions"
            ),
            inline=False,
        )

        embed.add_field(
            name="⏰ Schedule Commands",
            value="`/toggle_scheduled_news [all/category]` - Toggle daily 9 AM GMT+8 posts",
            inline=False,
        )

        embed.add_field(
            name="🛠️ Utility Commands",
            value=(
                "`/ping` - Check bot latency\n"
                "`/help` - Show this help message"
            ),
            inline=False,
        )

        embed.set_footer(text="React with ❓ for more info on specific commands.")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
