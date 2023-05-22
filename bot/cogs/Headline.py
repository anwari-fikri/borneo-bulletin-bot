import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from scraper import scraper
import datetime
import json

utc = datetime.timezone.utc
time = datetime.time(
    hour=1, minute=00, tzinfo=utc
)  # 1am utc = 9am gmt+8 (singapore time)

CHANNEL_HEADLINE = "./data/set_channel_headline.json"
TODAY_HEADLINE = "./scraper/data/today_headline.json"


class Headline(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        try:
            with open(CHANNEL_HEADLINE, "r") as f:
                self.set_channel = json.load(f)
        except FileNotFoundError:
            self.set_channel = []

        self.scheduled_fetch_headline.start()

    def cog_unload(self):
        with open(CHANNEL_HEADLINE, "w") as f:
            json.dump(self.set_channel, f)

    @app_commands.command(
        name="toggle_scheduled_headline",
        description="Enable/Disable scheduled headline fetching on this channel",
    )
    async def toggle_scheduled_headline(self, interaction: discord.Interaction):
        if interaction.channel_id not in self.set_channel:
            self.set_channel.append(interaction.channel_id)
            await interaction.response.send_message(
                content=f"Automated Headline Fetching is now **ENABLED** on #{interaction.channel}"
            )
        elif interaction.channel_id in self.set_channel:
            self.set_channel.remove(interaction.channel_id)
            await interaction.response.send_message(
                content=f"Automated Headline Fetching is now **DISABLED** on #{interaction.channel}"
            )

    @app_commands.command(
        name="fetch_headline", description="Fetch headline articles for today's date"
    )
    async def fetch_headline(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            "Retrieving articles. This may take up few minutes..."
        )

        today_headlines = self.fetch_headline_data()
        if today_headlines["article_data"] == []:
            await interaction.channel.send(
                embed=discord.Embed(description="No new headlines today ☹️")
            )
        else:
            for article_data in today_headlines["article_data"]:
                await asyncio.sleep(0.5)
                await self.send_article_embed(
                    channel=interaction.channel, article_data=article_data
                )

    @tasks.loop(time=time)
    async def scheduled_fetch_headline(self):
        if self.set_channel != []:
            for channel_id in self.set_channel:
                channel = await self.client.fetch_channel(channel_id)
                today_headlines = self.fetch_headline_data()
                if today_headlines["article_data"] == []:
                    await channel.send(
                        embed=discord.Embed(description="No new headline today ☹️")
                    )
                else:
                    for article_data in today_headlines["article_data"]:
                        await asyncio.sleep(0.5)
                        await self.send_article_embed(
                            channel=channel, article_data=article_data
                        )

    async def send_article_embed(
        self, channel: discord.TextChannel, article_data: dict
    ):
        embed = discord.Embed(
            title=article_data["title"],
            url=article_data["url"],
            description=article_data["content_text"][:1500],
            color=discord.Color.yellow(),
        )
        embed.set_author(name=article_data["author"])
        embed.set_image(url=article_data["image_url"])

        await channel.send(embed=embed)

    def fetch_headline_data(self):
        try:
            with open(TODAY_HEADLINE, "r") as f:
                today_headlines = json.load(f)
        except FileNotFoundError as e:
            print("JSON file not found: %s", e)
            today_headlines = {
                "date": "",
                "article_data": {
                    "url": "",
                    "title": "",
                    "author": "",
                    "content_text": "",
                },
            }

        today_date = datetime.datetime.today().strftime("%Y-%m-%d")
        if today_headlines["date"] != today_date:
            today_headlines = scraper.main_headline()
        return today_headlines


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Headline(client))
