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

CHANNEL_NATIONAL = "./data/set_channel_national.json"
TODAY_NATIONAL = "./scraper/data/today_national.json"


class National(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        try:
            with open(CHANNEL_NATIONAL, "r") as f:
                self.set_channel = json.load(f)
        except FileNotFoundError:
            self.set_channel = []

        self.scheduled_fetch_national.start()

    def cog_unload(self):
        with open(CHANNEL_NATIONAL, "w") as f:
            json.dump(self.set_channel, f)

    @app_commands.command(name="national", description="national test")
    async def national(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("National")

    @app_commands.command(
        name="toggle_scheduled_national",
        description="Enable/Disable scheduled National news fetching on this channel",
    )
    async def toggle_scheduled_national(self, interaction: discord.Interaction):
        if interaction.channel_id not in self.set_channel:
            self.set_channel.append(interaction.channel_id)
            await interaction.response.send_message(
                content=f"Automated National News Fetching is now **ENABLED** on #{interaction.channel}"
            )
        elif interaction.channel_id in self.set_channel:
            self.set_channel.remove(interaction.channel_id)
            await interaction.response.send_message(
                content=f"Automated National News Fetching is now **DISABLED** on #{interaction.channel}"
            )

    @app_commands.command(
        name="fetch_national", description="Fetch national articles for today's date"
    )
    async def fetch_national(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            "Retrieving articles. This may take up few minutes..."
        )

        today_national = self.fetch_national_data()
        if today_national["article_data"] == []:
            await interaction.channel.send(
                embed=discord.Embed(description="No new national news today ☹️")
            )
        else:
            for article_data in today_national["article_data"]:
                await asyncio.sleep(0.5)
                await self.send_article_embed(
                    channel=interaction.channel, article_data=article_data
                )

    @tasks.loop(time=time)
    async def scheduled_fetch_national(self):
        if self.set_channel != []:
            for channel_id in self.set_channel:
                channel = await self.client.fetch_channel(channel_id)
                today_nationals = self.fetch_national_data()
                if today_nationals["article_data"] == []:
                    await channel.send(
                        embed=discord.Embed(description="No new national news today ☹️")
                    )
                else:
                    for article_data in today_nationals["article_data"]:
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
            color=discord.Color.red(),
        )
        embed.set_author(name=article_data["author"])
        embed.set_image(url=article_data["image_url"])

        await channel.send(embed=embed)

    def fetch_national_data(self):
        try:
            with open(TODAY_NATIONAL, "r") as f:
                today_national = json.load(f)
        except FileNotFoundError as e:
            print("JSON file not found: %s", e)
            today_national = {
                "date": "",
                "article_data": {
                    "url": "",
                    "title": "",
                    "author": "",
                    "content_text": "",
                },
            }

        today_date = datetime.datetime.today().strftime("%Y-%m-%d")
        if today_national["date"] != today_date:
            today_national = scraper.main_national()
        return today_national


async def setup(client: commands.Bot) -> None:
    await client.add_cog(National(client))
