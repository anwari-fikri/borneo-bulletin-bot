import discord
from cogs import responses
from scraper import scraper
import os
import asyncio


class BorneoBulletinBotClient(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"{self.user} is now running")

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        
        if message.content.startswith("whats brewing today"):
            print(f"{message.author} said: {message.content}")
            msg = await message.channel.send("Retrieving articles...")
            responses = scraper.fake_return()
            await msg.delete()
            for response in responses:
                # Format the message using Discord's markdown syntax
                message_text = f"```**{response['title']}**\nby *{response['author']}*\n\n{response['content_text'][:1500]}```"
                
                await message.channel.send(message_text)
                message_text = message_text
                await asyncio.sleep(1)


def main():
    TOKEN = os.getenv("TOKEN")
    intents = discord.Intents.default()
    intents.message_content = True
    client = BorneoBulletinBotClient(intents=intents)
    client.run(TOKEN)


if __name__ == "__main__":
    main()
