import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import asyncio
from db_handler import DatabaseHandler

ANIME_ENDPOINTS = {
    "dog": "https://api.thedogapi.com/v1/images/search",
    "cat": "https://api.thecatapi.com/v1/images/search",
    "fox": "https://randomfox.ca/floof/",
    "anime": "https://api.waifu.pics/sfw/waifu",
    "neko": "https://api.waifu.pics/sfw/neko",
    "megumin": "https://api.waifu.pics/sfw/megumin",
    "shinobu": "https://api.waifu.pics/sfw/shinobu"
}

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
        if db_gif:
            return db_gif.url

        # Try related fallback
        if gif_type not in ANIME_ENDPOINTS:
            gif_type = random.choice(list(ANIME_ENDPOINTS.keys()))

        endpoint = ANIME_ENDPOINTS[gif_type]
        try:
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    if gif_type in ["dog", "cat"]:
                        return data[0]["url"]
                    elif gif_type == "fox":
                        return data["image"]
                    else:
                        return data["url"]
        except Exception as e:
            print(f"Error fetching GIF: {e}")

        return "https://media.giphy.com/media/VgIums4vgV4iY/giphy.gif"

    async def get_gif_embed(self, gif_type):
        url = await self.get_gif_url(gif_type)
        titles = {
            "dog": "🐶 Woof! Here's a cute doggo!",
            "cat": "😺 Meow! Here's a cute kitty!",
            "fox": "🦊 What does the fox say?",
            "anime": "✨ Random Anime GIF",
            "neko": "😸 Neko GIF",
            "megumin": "💥 Megumin!",
            "shinobu": "🦋 Shinobu Moment"
        }

        colors = {
            "dog": discord.Color.from_rgb(133, 94, 66),
            "cat": discord.Color.from_rgb(255, 165, 0),
            "fox": discord.Color.from_rgb(255, 69, 0),
            "anime": discord.Color.from_rgb(255, 105, 180),
            "neko": discord.Color.from_rgb(255, 192, 203),
            "megumin": discord.Color.from_rgb(255, 0, 0),
            "shinobu": discord.Color.from_rgb(155, 89, 182)
        }

        title = titles.get(gif_type, f"🎭 Random {gif_type.title()} GIF")
        color = colors.get(gif_type, discord.Color.blurple())

        embed = discord.Embed(
            title=title,
            color=color
        )
        embed.set_image(url=url)
        embed.set_footer(text=f"Type: {gif_type.title()} • Auto-deletes in 60s")

        return embed

    @app_commands.command(name="gif", description="🎭 Show a random GIF of a specified type")
    @app_commands.describe(type="Type of GIF to show (dog, cat, fox, anime, neko, etc.)")
    async def gif_slash(self, interaction: discord.Interaction, type: str = "dog"):
        gif_type = type.lower().strip()
        embed = await self.get_gif_embed(gif_type)
        view = GifButton(self, interaction, gif_type)
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        await asyncio.sleep(60)
        try:
            await msg.delete()
        except:
            pass

    @commands.command(name="gif", help="🎭 Show a random GIF of a specified type")
    async def gif_prefix(self, ctx, gif_type: str = "dog"):
        gif_type = gif_type.lower().strip()
        embed = await self.get_gif_embed(gif_type)
        view = GifButton(self, ctx, gif_type)
        msg = await ctx.send(embed=embed, view=view)
        await asyncio.sleep(60)
        try:
            await msg.delete()
        except:
            pass

    @app_commands.command(name="addgif", description="🖼️ Add a custom GIF to the bot's collection")
    @app_commands.describe(
        category="Category for the GIF (dog, cat, anime, etc.)",
        url="URL of the GIF to add"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_gif_slash(self, interaction: discord.Interaction, category: str, url: str):
        category = category.lower().strip()

        if not (url.endswith(".gif") or url.endswith(".png") or url.endswith(".jpg") or 
                url.endswith(".jpeg") or "giphy.com" in url or "tenor.com" in url):
            await interaction.response.send_message(
                "❌ Invalid URL format. Please provide a direct link to a GIF or image."
            )
            msg = await interaction.original_response()
            await asyncio.sleep(10)
            try:
                await msg.delete()
            except:
                pass
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
            msg = await interaction.original_response()
            await asyncio.sleep(60)
            try:
                await msg.delete()
            except:
                pass
        else:
            await interaction.response.send_message(
                "❌ Failed to add GIF to the database. Please try again later."
            )
            msg = await interaction.original_response()
            await asyncio.sleep(10)
            try:
                await msg.delete()
            except:
                pass

    @commands.command(name="addgif", help="🖼️ Add a custom GIF to the bot's collection")
    @commands.has_permissions(manage_guild=True)
    async def add_gif_prefix(self, ctx, category: str, url: str):
        category = category.lower().strip()

        if not (url.endswith(".gif") or url.endswith(".png") or url.endswith(".jpg") or 
                url.endswith(".jpeg") or "giphy.com" in url or "tenor.com" in url):
            await ctx.send("❌ Invalid URL format. Please provide a direct link to a GIF or image.", delete_after=10)
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
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(60)
            try:
                await msg.delete()
            except:
                pass
        else:
            await ctx.send("❌ Failed to add GIF to the database. Please try again later.", delete_after=10)

async def setup(bot):
    await bot.add_cog(GifCog(bot))
    print("✅ GifCog loaded!")
    await bot.tree.sync()
    print("🔄 Synced slash commands!")
    # Load the database handler
    DatabaseHandler.load_database()
    print("📦 Database loaded!")
