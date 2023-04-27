import discord
from discord.ext import commands, tasks
from discord import app_commands
from scraper import scraper
import datetime
import asyncio

utc = datetime.timezone.utc
time = datetime.time(hour=7, minute=23, tzinfo=utc)

class cog1(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.scheduled_fetch_article.start()

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
            embed.set_image(url=response["image_url"])

            await interaction.followup.send(embed=embed)
            await asyncio.sleep(1)
    
    @tasks.loop(time=time)
    async def scheduled_fetch_article(self):
        channel = await self.client.fetch_channel(1097395352291770441)  # replace with your channel ID
        responses = scraper.fake_return()
        for response in responses:
            embed = discord.Embed(
                title=response["title"],
                url=response["url"],
                description=response["content_text"][:1500],
                color=0x00FF00,
            )
            embed.set_author(name=response["author"])
            embed.set_image(url=response["image_url"])

            await channel.send(embed=embed)
            await asyncio.sleep(1)



async def setup(client: commands.Bot) -> None:
    await client.add_cog(cog1(client))
