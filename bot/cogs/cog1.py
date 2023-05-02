import discord
from discord.ext import commands, tasks
from discord import app_commands
from scraper import scraper
import datetime
import asyncio

utc = datetime.timezone.utc
time = datetime.time(hour=1, minute=00, tzinfo=utc) # 1am utc = 9am gmt+8 (singapore time)

class cog1(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.set_channel = []
        self.scheduled_fetch_article.start()

    @app_commands.command(name="toggle_scheduled_news", description="Enable/Disable scheduled news fetching on this channel")
    async def toggle_scheduled_news(self, interaction: discord.Interaction):
        if interaction.channel_id not in self.set_channel:
            self.set_channel.append(interaction.channel_id)
            await interaction.response.send_message(content=f"Automated News Fetching is now **ENABLED** on #{interaction.channel}")
        elif interaction.channel_id in self.set_channel:
            self.set_channel.remove(interaction.channel_id)
            await interaction.response.send_message(content=f"Automated News Fetching is now **DISABLED** on #{interaction.channel}")


    @app_commands.command(name="fetch_article", description="Fetch articles")
    async def fetch_article(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("Retrieving articles. This may take up to 1 minute...")

        responses = await asyncio.to_thread(scraper.fake_return)
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
        if self.set_channel != []:
            for channel_id in self.set_channel:
                channel = await self.client.fetch_channel(channel_id)  # replace with your channel ID
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

                    await channel.send(embed=embed)
                    await asyncio.sleep(1)



async def setup(client: commands.Bot) -> None:
    await client.add_cog(cog1(client))
