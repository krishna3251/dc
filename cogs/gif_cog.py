import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import os

GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")  # From your .env

class GifCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def search_gif(self, query: str):
        url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q={query}&limit=10"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                gifs = data.get("data", [])
                if not gifs:
                    return None
                return random.choice(gifs)["images"]["original"]["url"]

    async def perform_action(self, interaction: discord.Interaction, action: str, target: discord.Member):
        gif_url = await self.search_gif(action)
        if not gif_url:
            await interaction.response.send_message("Couldn't find a gif, sorry!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{interaction.user.display_name} {action}s {target.display_name}!",
            color=discord.Color.orange()
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hug", description="Give someone a warm hug!")
    async def hug(self, interaction: discord.Interaction, target: discord.Member):
        await self.perform_action(interaction, "hug", target)

    @app_commands.command(name="kiss", description="Give someone a kiss!")
    async def kiss(self, interaction: discord.Interaction, target: discord.Member):
        await self.perform_action(interaction, "kiss", target)

    @app_commands.command(name="slap", description="Slap someone playfully!")
    async def slap(self, interaction: discord.Interaction, target: discord.Member):
        await self.perform_action(interaction, "slap", target)

    async def cog_load(self):
        self.bot.tree.add_command(self.hug)
        self.bot.tree.add_command(self.kiss)
        self.bot.tree.add_command(self.slap)

async def setup(bot):
    await bot.add_cog(GifCog(bot))
