import datetime
import discord
from scraper import scraper
import os
import asyncio


class BorneoBulletinBotClient(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"{self.user} is now running")
        
        self.loop.create_task(self.send_good_afternoon())

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        
        if message.content.startswith("whats brewing today"):
            print(f"{message.author} said: {message.content}")
            msg = await message.channel.send("Retrieving articles...")
            responses = scraper.fake_return()
            await msg.delete()
            for response in responses:
                # Create a new embed
                embed = discord.Embed(title=response['title'], url=response['url'], description=response['content_text'][:1500], color=0x00ff00)
                embed.set_author(name=response['author'])
                await message.channel.send(embed=embed)
                await asyncio.sleep(1)

    async def send_good_afternoon(self):
        # Get the current time
        now = datetime.datetime.now()

        # If the current time is before 4:30 pm, sleep until 4:30 pm
        if now.hour < 16 or (now.hour == 16 and now.minute < 55):
            delta = datetime.datetime(now.year, now.month, now.day, 16, 55) - now
            await asyncio.sleep(delta.total_seconds())

        # Get the channel by ID
        channel = self.get_channel(1097395352291770441)

        # Send the "good afternoon" message
        await channel.send("Good afternoon!")



def main():
    TOKEN = os.getenv("TOKEN")
    intents = discord.Intents.default()
    intents.message_content = True
    client = BorneoBulletinBotClient(intents=intents)
    client.run(TOKEN)


if __name__ == "__main__":
    main()
