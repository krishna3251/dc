import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import os
from typing import Optional

GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

class GifCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def search_gif(self, query: str):
        url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q={query}&limit=10"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                gifs = data.get("data")
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

    # Slash command: /hug
    @app_commands.command(name="hug", description="Give someone a hug!")
    async def hug(self, interaction: discord.Interaction, target: Optional[discord.Member] = None):
        if target is None:
            target = interaction.user
        await self.perform_action(interaction, "hug", target)

    # Slash command: /kiss
    @app_commands.command(name="kiss", description="Give someone a kiss!")
    async def kiss(self, interaction: discord.Interaction, target: Optional[discord.Member] = None):
        if target is None:
            target = interaction.user
        await self.perform_action(interaction, "kiss", target)

    # Slash command: /slap
    @app_commands.command(name="slap", description="Slap someone playfully!")
    async def slap(self, interaction: discord.Interaction, target: Optional[discord.Member] = None):
        if target is None:
            target = interaction.user
        await self.perform_action(interaction, "slap", target)

    async def cog_load(self):
        # Register commands to the app command tree when the cog is loaded
        self.bot.tree.add_command(self.hug)
        self.bot.tree.add_command(self.kiss)
        self.bot.tree.add_command(self.slap)

async def setup(bot):
    await bot.add_cog(GifCog(bot))
