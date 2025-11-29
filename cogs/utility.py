"""
Utility cog: /ping, /commands.
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
                "`/read_full [category]` - Read full articles in a thread for discussion\n"
                "`/categories` - List all available categories\n"
                "*Scheduled posts send compact digests at 9 AM GMT+8; click 'Show more' to browse or 'Start thread' to discuss*"
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
            value=(
                "`/toggle_scheduled_news [all/category]` - Toggle daily 9 AM GMT+8 digest posts\n"
                "*Digests show top 5 headlines; click 'Show more' for full articles or 'Start thread' to discuss*"
            ),
            inline=False,
        )

        embed.add_field(
            name="🛠️ Utility Commands",
            value=(
                "`/ping` - Check bot latency\n"
                "`/commands` - Show this help message"
            ),
            inline=False,
        )

        embed.set_footer(text="React with ❓ for more info on specific commands.")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
