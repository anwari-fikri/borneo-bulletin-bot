import discord
from discord.ext import commands
from discord import app_commands
from scraper import scraper
import asyncio


class cog1(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="greet", description="Sends hello!")
    async def greet(self, interaction: discord.Interaction):
        await interaction.response.send_message(content="Hello!")

    @app_commands.command(name="fetch_article", description="Fetch articles")
    async def fetch_article(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("Retrieving articles. This may take up to 1 minute...")

        responses = scraper.main()
        for response in responses:
            embed = discord.Embed(
                title=response["title"],
                url=response["url"],
                description=response["content_text"][:1500],
                color=0x00FF00,
            )
            embed.set_author(name=response["author"])

            await interaction.followup.send(embed=embed)
            await asyncio.sleep(1)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(cog1(client))
