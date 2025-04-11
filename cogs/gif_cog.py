import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import os
from db_handler import DatabaseHandler

class GifButton(discord.ui.View):
    def __init__(self, cog, ctx_or_interaction, gif_type):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx_or_interaction = ctx_or_interaction
        self.gif_type = gif_type

    @discord.ui.button(label="🔄 New GIF", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = await self.cog.get_gif_embed(self.gif_type)
        await interaction.edit_original_response(embed=embed, view=self)

class GifCog(commands.Cog):
    """🎭 GIF System - Random GIFs from Tenor and Giphy!"""

    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.tenor_key = os.getenv('TENOR_API_KEY')
        self.giphy_key = os.getenv('GIPHY_API_KEY')

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

    async def get_gif_url(self, search_term):
        # Try Tenor first
        gif_url = await self.get_tenor_gif(search_term)
        if gif_url:
            return gif_url, 'Tenor'

        # Try Giphy as fallback
        gif_url = await self.get_giphy_gif(search_term)
        if gif_url:
            return gif_url, 'Giphy'

        return "https://media.giphy.com/media/VgIums4vgV4iY/giphy.gif", 'Fallback'

    async def get_gif_embed(self, search_term):
        url, source = await self.get_gif_url(search_term)

        embed = discord.Embed(
            title=f"🎭 {search_term.title()} GIF",
            color=discord.Color.random()
        )
        embed.set_image(url=url)
        embed.set_footer(text=f"Source: {source} • Click the button for another GIF!")
        return embed

    @app_commands.command(name="gif", description="🎭 Show a random GIF from Tenor/Giphy")
    @app_commands.describe(search="What kind of GIF to search for")
    async def gif_slash(self, interaction: discord.Interaction, search: str = "random"):
        search_term = search.lower().strip()
        embed = await self.get_gif_embed(search_term)
        view = GifButton(self, interaction, search_term)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="gif", help="🎭 Show a random GIF from Tenor/Giphy")
    async def gif_prefix(self, ctx, *, search: str = "random"):
        search_term = search.lower().strip()
        embed = await self.get_gif_embed(search_term)
        view = GifButton(self, ctx, search_term)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(
        name="addgif",
        description="🖼️ Add a custom GIF to the bot's collection")
    @app_commands.describe(
        category="Category for the GIF (dog, cat, anime, etc.)",
        url="URL of the GIF to add")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_gif_slash(self, interaction: discord.Interaction,
                            category: str, url: str):
        """Add a custom GIF to the database (slash command)"""
        # Normalize the category
        category = category.lower().strip()

        # Verify URL format
        if not (url.endswith(".gif") or url.endswith(".png")
                or url.endswith(".jpg") or url.endswith(".jpeg")
                or "giphy.com" in url or "tenor.com" in url):
            await interaction.response.send_message(
                "❌ Invalid URL format. Please provide a direct link to a GIF or image.",
                ephemeral=True)
            return

        # Add to database
        success = DatabaseHandler.add_anime_gif(category, url)

        if success:
            embed = discord.Embed(
                title="✅ GIF Added Successfully",
                description=f"Added a new {category} GIF to the collection!",
                color=discord.Color.green())
            embed.set_image(url=url)
            embed.set_footer(text=f"Added by {interaction.user.name}")

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                "❌ Failed to add GIF to the database. Please try again later.",
                ephemeral=True)

    @commands.command(name="addgif",
                      help="🖼️ Add a custom GIF to the bot's collection")
    @commands.has_permissions(manage_guild=True)
    async def add_gif_prefix(self, ctx, category: str, url: str):
        """Add a custom GIF to the database (prefix command)"""
        # Normalize the category
        category = category.lower().strip()

        # Verify URL format
        if not (url.endswith(".gif") or url.endswith(".png")
                or url.endswith(".jpg") or url.endswith(".jpeg")
                or "giphy.com" in url or "tenor.com" in url):
            await ctx.send(
                "❌ Invalid URL format. Please provide a direct link to a GIF or image."
            )
            return

        # Add to database
        success = DatabaseHandler.add_anime_gif(category, url)

        if success:
            embed = discord.Embed(
                title="✅ GIF Added Successfully",
                description=f"Added a new {category} GIF to the collection!",
                color=discord.Color.green())
            embed.set_image(url=url)
            embed.set_footer(text=f"Added by {ctx.author.name}")

            await ctx.send(embed=embed)
        else:
            await ctx.send(
                "❌ Failed to add GIF to the database. Please try again later.")


async def setup(bot):
    await bot.add_cog(GifCog(bot))
    print("✅ GifCog loaded!")