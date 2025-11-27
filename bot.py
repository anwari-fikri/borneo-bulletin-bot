# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Bot setup
bot = commands.Bot(command_prefix="/", intents=intents)

COGS_DIR = Path(__file__).parent / "cogs"


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    await bot.tree.sync()
    print("✅ Slash commands synced.")


async def load_cogs():
    """Load all cogs from the cogs directory."""
    if not COGS_DIR.exists():
        COGS_DIR.mkdir()
        print(f"Created {COGS_DIR} directory.")
    
    for cog_file in COGS_DIR.glob("*.py"):
        if cog_file.name.startswith("_"):
            continue
        cog_name = f"cogs.{cog_file.stem}"
        try:
            await bot.load_extension(cog_name)
            print(f"✅ Loaded cog: {cog_name}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog_name}: {e}")


async def main():
    async with bot:
        await load_cogs()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN not found in .env")
        await bot.start(token)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
