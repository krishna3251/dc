import discord
from discord.ext import commands
from discord import app_commands
import googleapiclient.discovery
import googleapiclient.errors
from config import GOOGLE_API_KEY, GOOGLE_CSE_ID
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
            color=discord.Color.blue()
        )

        if "items" not in results or not results["items"]:
            embed.description = "❌ No results found."
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

    async def save_search_history(self, guild_id, user_id, query, result_count):
        """Save search query to history (optional)"""
        try:
            history_file = "search_history.json"
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    history = json.load(f)
            else:
                history = {"searches": []}

            history["searches"].append({
                "guild_id": str(guild_id),
                "user_id": str(user_id),
                "query": query,
                "result_count": result_count,
                "timestamp": str(discord.utils.utcnow())
            })

            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save search history: {e}")

    @commands.command(name="gsearch")
    async def gsearch_prefix(self, ctx, *, query: str):
        """Prefix command: Search Google."""
        await self.run_search(ctx, query=query, results=3)

    async def run_search(self, ctx_or_inter, query, results=3):
        results = max(1, min(5, results))

        async with ctx_or_inter.typing() if isinstance(ctx_or_inter, commands.Context) else ctx_or_inter.channel.typing():
            search_results, error = await self.search_google(query, results)

            if error:
                if isinstance(ctx_or_inter, commands.Context):
                    await ctx_or_inter.send(f"❌ {error}")
                else:
                    await ctx_or_inter.response.send_message(f"❌ {error}", ephemeral=True)
                return

            embed = self.create_search_embed(query, search_results)

            if isinstance(ctx_or_inter, commands.Context):
                await ctx_or_inter.send(embed=embed)
            else:
                await ctx_or_inter.response.send_message(embed=embed)

            await self.save_search_history(
                ctx_or_inter.guild.id if ctx_or_inter.guild else "DM",
                ctx_or_inter.user.id if isinstance(ctx_or_inter, discord.Interaction) else ctx_or_inter.author.id,
                query,
                results
            )

    @app_commands.command(name="googlesearch", description="🔍 Search Google and get results")
    @app_commands.describe(query="What do you want to search?", results="Number of results (1-5)")
    async def search_slash(self, interaction: discord.Interaction, query: str, results: int = 3):
        await self.run_search(interaction, query, results)

async def setup(bot):
    await bot.add_cog(GoogleSearchCog(bot))
    print("✅ Google Search Cog loaded")
