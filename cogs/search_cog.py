import discord
from discord.ext import commands
from discord import app_commands
import googleapiclient.discovery
import googleapiclient.errors
from config import GOOGLE_API_KEY, GOOGLE_CSE_ID
import asyncio
import os
import json

class GoogleSearchCog(commands.Cog):
    """🔍 Google Search Commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.search_service = None
        self.setup_google_api()

    def setup_google_api(self):
        """Initialize the Google API client."""
        try:
            self.search_service = googleapiclient.discovery.build(
                "customsearch", "v1", developerKey=GOOGLE_API_KEY
            )
            print("✅ Google Search API initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing Google Search API: {e}")
            self.search_service = None

    async def search_google(self, query, num_results=3):
        """Perform a Google search with the provided query."""
        if self.search_service is None:
            return None, "Google Search API is not available."
        
        try:
            search_results = self.search_service.cse().list(
                q=query,
                cx=GOOGLE_CSE_ID,
                num=num_results
            ).execute()
            
            return search_results, None
        except googleapiclient.errors.HttpError as e:
            return None, f"API Error: {e}"
        except Exception as e:
            return None, f"Error: {e}"

    def create_search_embed(self, query, results):
        """Create an embed with search results."""
        embed = discord.Embed(
            title=f"🔍 Google Search: {query}",
            color=discord.Color.blue(),
            description="Here are the top results from Google."
        )
        
        if "items" not in results or not results["items"]:
            embed.description = "No results found."
            return embed
        
        for i, item in enumerate(results["items"], start=1):
            title = item.get("title", "No title")
            link = item.get("link", "No link")
            snippet = item.get("snippet", "No description")
            
            embed.add_field(
                name=f"{i}. {title}",
                value=f"{snippet}\n[View Result]({link})",
                inline=False
            )
            
        embed.set_footer(text="Powered by Google")
        return embed

    @commands.hybrid_command(
        name="search",
        description="Search on Google and get results"
    )
    @app_commands.describe(
        query="What do you want to search for?",
        results="Number of results to show (1-5)"
    )
    async def save_search_history(self, guild_id, user_id, query, result_count):
        """Save search query to history (if a database connection is available)"""
        try:
            # Create a JSON record for storing the search history
            search_record = {
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "query": query,
                "result_count": result_count,
                "timestamp": str(discord.utils.utcnow())
            }
            
            # Save to a local JSON file as a fallback method
            history_file = "search_history.json"
            
            # Read existing history or create new
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r") as f:
                        history = json.load(f)
                except:
                    history = {"searches": []}
            else:
                history = {"searches": []}
            
            # Add new search record
            history["searches"].append(search_record)
            
            # Save updated history
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
                
            return True
        except Exception as e:
            print(f"❌ Error saving search history: {e}")
            return False

    async def search_command(self, ctx, *, query: str, results: int = 3):
        """Search Google and return results."""
        if not query:
            await ctx.send("⚠️ Please provide a search query.")
            return
        
        # Limit results between 1 and 5
        results = max(1, min(5, results))
        
        # Check if API credentials are available
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID or GOOGLE_API_KEY == "${GOOGLE_API_KEY}" or GOOGLE_CSE_ID == "${GOOGLE_CSE_ID}":
            await ctx.send("❌ Google API credentials are not properly configured. Please add valid GOOGLE_API_KEY and GOOGLE_CSE_ID to your environment variables.")
            return
        
        async with ctx.typing():
            # Show that the bot is "typing" while searching
            search_results, error = await self.search_google(query, results)
            
            if error:
                await ctx.send(f"❌ Error: {error}")
                return
            
            # Record the search in history database
            await self.save_search_history(
                ctx.guild.id if ctx.guild else "DM",
                ctx.author.id,
                query,
                results
            )
                
            embed = self.create_search_embed(query, search_results)
            await ctx.send(embed=embed)

    @commands.command(name="gsearch")
    async def gsearch_prefix(self, ctx, *, query: str):
        """Classic prefix command for searching Google."""
        await self.search_command(ctx, query=query, results=3)

    @app_commands.command(
        name="googlesearch",
        description="Search the web using Google"
    )
    @app_commands.describe(
        query="What do you want to search for?",
        results="Number of results to show (1-5)"
    )
    async def search_slash(self, interaction: discord.Interaction, query: str, results: int = 3):
        """Slash command for searching Google."""
        ctx = await self.bot.get_context(interaction)
        await self.search_command(ctx, query=query, results=results)

async def setup(bot):
    await bot.add_cog(GoogleSearchCog(bot))
    print("✅ Google Search cog loaded")