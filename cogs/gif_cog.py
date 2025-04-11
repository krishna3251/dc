import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import os

class GifButton(discord.ui.View):
    def __init__(self, cog, ctx_or_interaction, gif_type):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx_or_interaction = ctx_or_interaction
        self.gif_type = gif_type
        self.expired = False

    async def on_timeout(self):
        self.expired = True
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title=f"🎭 {self.gif_type.title()} GIF",
            description="This session has expired. Please use the command again.",
            color=discord.Color.dark_gray()
        )
        embed.set_footer(text="Session expired")

        try:
            await self.ctx_or_interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            print(f"Error editing expired message: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.expired:
            await interaction.response.send_message("This button is no longer active. Please use the command again!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔄 New GIF", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self.cog.get_gif_embed(self.gif_type)
        await interaction.edit_original_response(embed=embed, view=self)

class GifCog(commands.Cog):
    """🎭 GIF System - Random GIFs from AnimeGIF API, Tenor, and Giphy!"""

    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.tenor_key = os.getenv('TENOR_API_KEY')
        self.giphy_key = os.getenv('GIPHY_API_KEY')
        self.custom_api_key = "ejIGCMPV65yS5BtPsbg6BtNsI1WUOHyU"

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def get_tenor_gif(self, search_term):
        url = f"https://tenor.googleapis.com/v2/search?q={search_term}&key={self.tenor_key}&limit=20"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['results']:
                        result = random.choice(data['results'])
                        return result['media_formats']['gif']['url']
        except Exception as e:
            print(f"Tenor API error: {e}")
        return None

    async def get_giphy_gif(self, search_term):
        url = f"https://api.giphy.com/v1/gifs/search?api_key={self.giphy_key}&q={search_term}&limit=20"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['data']:
                        result = random.choice(data['data'])
                        return result['images']['original']['url']
        except Exception as e:
            print(f"Giphy API error: {e}")
        return None

    async def get_custom_gif(self, search_term):
        url = f"https://animegif.xyz/api/gif?key={self.custom_api_key}&tag={search_term}"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("url"):
                        return data["url"], "AnimeGIF"
        except Exception as e:
            print(f"AnimeGIF API error: {e}")
        return None, None

    async def get_gif_url(self, search_term):
        gif_url, source = await self.get_custom_gif(search_term)
        if gif_url:
            return gif_url, source

        gif_url = await self.get_tenor_gif(search_term)
        if gif_url:
            return gif_url, 'Tenor'

        gif_url = await self.get_giphy_gif(search_term)
        if gif_url:
            return gif_url, 'Giphy'

        return None, None  # No fallback!

    async def get_gif_embed(self, search_term):
        url, source = await self.get_gif_url(search_term)

        if not url:
            embed = discord.Embed(
                title="❌ No GIF Found",
                description=f"Could not find any GIFs for `{search_term}`.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Try a different keyword.")
            return embed

        embed = discord.Embed(
            title=f"🎭 {search_term.title()} GIF",
            color=discord.Color.random()
        )
        embed.set_image(url=url)
        embed.set_footer(text=f"Source: {source} • Click the button for another GIF!")
        return embed

    @app_commands.command(name="gif", description="🎭 Show a random GIF from AnimeGIF, Tenor, or Giphy")
    @app_commands.describe(search="What kind of GIF to search for")
    async def gif_slash(self, interaction: discord.Interaction, search: str = "random"):
        search_term = search.lower().strip()
        embed = await self.get_gif_embed(search_term)
        view = GifButton(self, interaction, search_term)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="gif", help="🎭 Show a random GIF from AnimeGIF, Tenor, or Giphy")
    async def gif_prefix(self, ctx, *, search: str = "random"):
        search_term = search.lower().strip()
        embed = await self.get_gif_embed(search_term)
        view = GifButton(self, ctx, search_term)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(GifCog(bot))
    print("✅ GifCog loaded!")
