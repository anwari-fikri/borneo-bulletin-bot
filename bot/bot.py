import datetime
import discord
from scraper import scraper
import os
import asyncio


class BorneoBulletinBotClient(discord.Client):
    def __init__(self, intents=None):
        super().__init__(intents=intents)
        self.enabled_channels = set()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"{self.user} is now running")
        
        self.loop.create_task(self.schedule_news())

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        
        if message.content.startswith("whats brewing today"):
            print(f"{message.author} said: {message.content}")
            await self.retrieve_articles(message.channel)

        if message.content == "!enable_news":
            self.enabled_channels.add(message.channel.id)
            await message.channel.send("News bot enabled on this channel")
        elif message.content == "!disable_news":
            self.enabled_channels.remove(message.channel.id)
            await message.channel.send("News bot enabled on this channel")

    async def schedule_news(self):
        await self.wait_until_ready()
        now = datetime.datetime.now()

        if now.hour < 14 or (now.hour == 14 and now.minute < 41):
            delta = datetime.datetime(now.year, now.month, now.day, 14, 41) - now
            await asyncio.sleep(delta.total_seconds())

            for channel_id in self.enabled_channels:
                channel = self.get_channel(channel_id)
                await self.retrieve_articles(channel)

    async def retrieve_articles(self, channel):
        msg = await channel.send("Retrieving articles...")
        responses = scraper.fake_return()
        await msg.delete()
        for response in responses:
            embed = discord.Embed(title=response['title'], url=response['url'], description=response['content_text'][:1500], color=0x00ff00)
            embed.set_author(name=response['author'])
            await channel.send(embed=embed)
            await asyncio.sleep(1)



def main():
    TOKEN = os.getenv("TOKEN")
    intents = discord.Intents.default()
    intents.message_content = True
    client = BorneoBulletinBotClient(intents=intents)
    client.run(TOKEN)


if __name__ == "__main__":
    main()
