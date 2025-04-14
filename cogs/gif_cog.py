import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import os
from db_handler import DatabaseHandler

GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

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
    """🎭 Anime & Animal GIF System - Random GIFs on demand!"""

    def __init__(self, bot):
        self.bot = bot
        self.session = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def get_gif_url(self, gif_type):
        db_gif = DatabaseHandler.get_random_gif(category=gif_type)
        if db_gif and (".gif" in db_gif.url or "giphy.com" in db_gif.url or "tenor.com" in db_gif.url):
            return db_gif.url

        try:
            url = (
                f"https://api.giphy.com/v1/gifs/search"
                f"?api_key={GIPHY_API_KEY}&q={gif_type}&limit=25&offset=0&rating=pg&lang=en"
            )
            async with self.session.get(url) as resp:
                data = await resp.json()
                if data.get("data"):
                    gifs = data["data"]
                    random_gif = random.choice(gifs)
                    return random_gif["images"]["original"]["url"]
        except Exception as e:
            print(f"[Giphy Error] {e}")

        return "https://media.giphy.com/media/VgIums4vgV4iY/giphy.gif"

    async def get_gif_embed(self, gif_type):
        url = await self.get_gif_url(gif_type)
        embed = discord.Embed(
            title=f"🎭 Random {gif_type.title()} GIF",
            color=discord.Color.random()
        )
        embed.set_image(url=url)
        embed.set_footer(text=f"Type: {gif_type.title()} • Click the button for another GIF!")
        return embed

    @app_commands.command(name="gif", description="🎭 Show a random GIF of a specified type")
    @app_commands.describe(type="Type of GIF to show (e.g. dog, cat, anime, etc.)")
    async def gif_slash(self, interaction: discord.Interaction, type: str = "dog"):
        gif_type = type.lower().strip()
        embed = await self.get_gif_embed(gif_type)
        view = GifButton(self, interaction, gif_type)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="gif", help="🎭 Show a random GIF of a specified type")
    async def gif_prefix(self, ctx, gif_type: str = "dog"):
        gif_type = gif_type.lower().strip()
        embed = await self.get_gif_embed(gif_type)
        view = GifButton(self, ctx, gif_type)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="addgif", description="🖼️ Add a custom GIF to the bot's collection")
    @app_commands.describe(
        category="Category for the GIF (e.g. dog, cat, anime, etc.)",
        url="URL of the GIF to add"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_gif_slash(self, interaction: discord.Interaction, category: str, url: str):
        category = category.lower().strip()
        if not (url.endswith(('.gif', '.png', '.jpg', '.jpeg')) or "giphy.com" in url or "tenor.com" in url):
            await interaction.response.send_message("❌ Invalid URL format. Please provide a direct image link.", ephemeral=True)
            return
        success = DatabaseHandler.add_anime_gif(category, url)
        if success:
            embed = discord.Embed(
                title="✅ GIF Added Successfully",
                description=f"Added a new {category} GIF to the collection!",
                color=discord.Color.green()
            )
            embed.set_image(url=url)
            embed.set_footer(text=f"Added by {interaction.user.name}")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to add GIF to the database.", ephemeral=True)

    @commands.command(name="addgif", help="🖼️ Add a custom GIF to the bot's collection")
    @commands.has_permissions(manage_guild=True)
    async def add_gif_prefix(self, ctx, category: str, url: str):
        category = category.lower().strip()
        if not (url.endswith(('.gif', '.png', '.jpg', '.jpeg')) or "giphy.com" in url or "tenor.com" in url):
            await ctx.send("❌ Invalid URL format. Please provide a direct image link.")
            return
        success = DatabaseHandler.add_anime_gif(category, url)
        if success:
            embed = discord.Embed(
                title="✅ GIF Added Successfully",
                description=f"Added a new {category} GIF to the collection!",
                color=discord.Color.green()
            )
            embed.set_image(url=url)
            embed.set_footer(text=f"Added by {ctx.author.name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to add GIF to the database.")

async def setup(bot):
    await bot.add_cog(GifCog(bot))
    print("✅ GifCog with Giphy API loaded!")
