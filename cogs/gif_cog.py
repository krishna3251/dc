import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
from db_handler import DatabaseHandler

# List of popular anime GIF APIs
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
        """Get a new random GIF of the same type"""
        await interaction.response.defer()
        
        # Get a new GIF and edit the message
        embed = await self.cog.get_gif_embed(self.gif_type)
        await interaction.edit_original_response(embed=embed, view=self)

class GifCog(commands.Cog):
    """🎭 Anime & Animal GIF System - Random GIFs on demand!"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = None  # Will be initialized in cog_load
        
    async def cog_load(self):
        """Initialize HTTP session when cog is loaded"""
        self.session = aiohttp.ClientSession()
        
    async def cog_unload(self):
        """Close HTTP session when cog is unloaded"""
        if self.session:
            await self.session.close()
    
    async def get_gif_url(self, gif_type):
        """Fetch a GIF URL from the appropriate API based on type"""
        # First check the database for custom GIFs
        db_gif = DatabaseHandler.get_random_gif(category=gif_type)
        if db_gif:
            return db_gif.url
        
        # If no custom GIF found, use external APIs
        if gif_type not in ANIME_ENDPOINTS:
            # Default to a random type if not found
            gif_type = random.choice(list(ANIME_ENDPOINTS.keys()))
            
        endpoint = ANIME_ENDPOINTS[gif_type]
        try:
            async with self.session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Different APIs have different response formats
                    if gif_type in ["dog", "cat"]:
                        return data[0]["url"]
                    elif gif_type == "fox":
                        return data["image"]
                    else:  # anime APIs
                        return data["url"]
                        
        except Exception as e:
            print(f"Error fetching GIF: {e}")
            # Fallback to a reliable GIF if API fails
            return "https://media.giphy.com/media/VgIums4vgV4iY/giphy.gif"
    
    async def get_gif_embed(self, gif_type):
        """Create an embed with a random GIF of the specified type"""
        url = await self.get_gif_url(gif_type)
        
        # Custom titles and colors based on GIF type
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
            "dog": discord.Color.from_rgb(133, 94, 66),  # Brown
            "cat": discord.Color.from_rgb(255, 165, 0),  # Orange
            "fox": discord.Color.from_rgb(255, 69, 0),   # Red-orange
            "anime": discord.Color.from_rgb(255, 105, 180),  # Pink
            "neko": discord.Color.from_rgb(255, 192, 203),  # Light pink
            "megumin": discord.Color.from_rgb(255, 0, 0),  # Red
            "shinobu": discord.Color.from_rgb(155, 89, 182)  # Purple
        }
        
        title = titles.get(gif_type, f"🎭 Random {gif_type.title()} GIF")
        color = colors.get(gif_type, discord.Color.blurple())
        
        embed = discord.Embed(
            title=title,
            color=color
        )
        embed.set_image(url=url)
        embed.set_footer(text=f"Type: {gif_type.title()} • Click the button for another GIF!")
        
        return embed
    
    @app_commands.command(name="gif", description="🎭 Show a random GIF of a specified type")
    @app_commands.describe(type="Type of GIF to show (dog, cat, fox, anime, neko, etc.)")
    async def gif_slash(self, interaction: discord.Interaction, type: str = "dog"):
        """Send a random GIF with a button to get a new one"""
        # Normalize the type (lowercase, strip spaces)
        gif_type = type.lower().strip()
        
        # Create the GIF embed
        embed = await self.get_gif_embed(gif_type)
        
        # Send with button for getting a new GIF
        view = GifButton(self, interaction, gif_type)
        await interaction.response.send_message(embed=embed, view=view)
    
    @commands.command(name="gif", help="🎭 Show a random GIF of a specified type")
    async def gif_prefix(self, ctx, gif_type: str = "dog"):
        """Send a random GIF with a button to get a new one (prefix version)"""
        # Normalize the type (lowercase, strip spaces)
        gif_type = gif_type.lower().strip()
        
        # Create the GIF embed
        embed = await self.get_gif_embed(gif_type)
        
        # Send with button for getting a new GIF
        view = GifButton(self, ctx, gif_type)
        await ctx.send(embed=embed, view=view)
    
    @app_commands.command(name="addgif", description="🖼️ Add a custom GIF to the bot's collection")
    @app_commands.describe(
        category="Category for the GIF (dog, cat, anime, etc.)",
        url="URL of the GIF to add"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_gif_slash(self, interaction: discord.Interaction, category: str, url: str):
        """Add a custom GIF to the database (slash command)"""
        # Normalize the category
        category = category.lower().strip()
        
        # Verify URL format
        if not (url.endswith(".gif") or url.endswith(".png") or url.endswith(".jpg") or 
                url.endswith(".jpeg") or "giphy.com" in url or "tenor.com" in url):
            await interaction.response.send_message(
                "❌ Invalid URL format. Please provide a direct link to a GIF or image.", 
                ephemeral=True
            )
            return
        
        # Add to database
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
            await interaction.response.send_message(
                "❌ Failed to add GIF to the database. Please try again later.",
                ephemeral=True
            )
    
    @commands.command(name="addgif", help="🖼️ Add a custom GIF to the bot's collection")
    @commands.has_permissions(manage_guild=True)
    async def add_gif_prefix(self, ctx, category: str, url: str):
        """Add a custom GIF to the database (prefix command)"""
        # Normalize the category
        category = category.lower().strip()
        
        # Verify URL format
        if not (url.endswith(".gif") or url.endswith(".png") or url.endswith(".jpg") or 
                url.endswith(".jpeg") or "giphy.com" in url or "tenor.com" in url):
            await ctx.send("❌ Invalid URL format. Please provide a direct link to a GIF or image.")
            return
        
        # Add to database
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
            await ctx.send("❌ Failed to add GIF to the database. Please try again later.")

async def setup(bot):
    await bot.add_cog(GifCog(bot))
    print("✅ GifCog loaded!")
