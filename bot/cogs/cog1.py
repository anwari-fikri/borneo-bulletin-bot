import discord
from discord.ext import commands, tasks
from discord import app_commands
from scraper import scraper
import datetime
import json

utc = datetime.timezone.utc
time = datetime.time(
    hour=1, minute=0, tzinfo=utc
)  # 1am utc = 9am gmt+8 (singapore time)


class cog1(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        # TODO: set channel must be stored in configuration file or environment variable so it doesn't clear when the bot restart
        self.set_channel = []
        self.scheduled_fetch_article.start()

    @app_commands.command(
        name="toggle_scheduled_news",
        description="Enable/Disable scheduled news fetching on this channel",
    )
    async def toggle_scheduled_news(self, interaction: discord.Interaction):
        if interaction.channel_id not in self.set_channel:
            self.set_channel.append(interaction.channel_id)
            await interaction.response.send_message(
                content=f"Automated News Fetching is now **ENABLED** on #{interaction.channel}"
            )
        elif interaction.channel_id in self.set_channel:
            self.set_channel.remove(interaction.channel_id)
            await interaction.response.send_message(
                content=f"Automated News Fetching is now **DISABLED** on #{interaction.channel}"
            )

    @app_commands.command(
        name="fetch_article", description="Fetch articles for today's date"
    )
    async def fetch_article(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            "Retrieving articles. This may take up few minutes..."
        )

        today_headlines = self.fetch_article_data()

        for article_data in today_headlines["article_data"]:
            await self.send_article_embed(
                channel=interaction.channel, article_data=article_data
            )

    @tasks.loop(time=time)
    async def scheduled_fetch_article(self):
        if self.set_channel != []:
            for channel_id in self.set_channel:
                channel = await self.client.fetch_channel(channel_id)
                today_headlines = self.fetch_article_data()
                for article_data in today_headlines["article_data"]:
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
            color=0x00FF00,
        )
        embed.set_author(name=article_data["author"])
        embed.set_image(url=article_data["image_url"])

        await channel.send(embed=embed)

    def fetch_article_data(self):
        try:
            with open("./scraper/today_headline.json", "r") as f:
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
            today_headlines = scraper.main()
        return today_headlines


async def setup(client: commands.Bot) -> None:
    await client.add_cog(cog1(client))
