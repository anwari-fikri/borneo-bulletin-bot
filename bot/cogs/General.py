import discord
from discord.ext import commands
from discord import app_commands


class General(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(
        name="help", description="Learn about Borneo Bulletin Bot commands"
    )
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embed = discord.Embed(
            title="Borneo Bulletin Bot Commands",
            description="Hello! I'm a news bot and I can help you stay up-to-date with the latest news from Borneo Bulletin Brunei. Below are the commands you can use to interact with me:",
            color=discord.Color.yellow(),
        )
        embed.add_field(name="NATIONAL", value="", inline=False)
        embed.add_field(
            name="/toggle_scheduled_national",
            value="Type this command in any text channel to receive a daily National news at 9am Brunei time.",
            inline=False,
        )
        embed.add_field(
            name="/fetch_national",
            value="Type this command in any text channel to receive the National news for the day immediately.",
            inline=False,
        )
        embed.add_field(name="HEADLINE", value="", inline=False)
        embed.add_field(
            name="/toggle_scheduled_headline",
            value="Type this command in any text channel to receive a daily news headline at 9am Brunei time.",
            inline=False,
        )
        embed.add_field(
            name="/fetch_headline",
            value="Type this command in any text channel to receive the news headlines for the day immediately.",
            inline=False,
        )
        embed.set_footer(
            text="That's it! Try these commands and stay informed with the latest news."
        )

        await interaction.followup.send(embed=embed)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(General(client))
