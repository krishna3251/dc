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
        self.search_service = self.setup_google_api()

    def setup_google_api(self):
        try:
            return googleapiclient.discovery.build(
                "customsearch", "v1", developerKey=GOOGLE_API_KEY
            )
        except Exception as e:
            print(f"❌ Failed to initialize Google Search API: {e}")
            return None

    async def search_google(self, query, num_results=3):
        if not self.search_service:
            return None, "Google Search API is not initialized."

        try:
            res = self.search_service.cse().list(
                q=query,
                cx=GOOGLE_CSE_ID,
                num=num_results
            ).execute()
            return res, None
        except googleapiclient.errors.HttpError as e:
            return None, f"Google API Error: {e}"
        except Exception as e:
            return None, f"Search failed: {e}"

    def create_embed(self, query, results):
        embed = discord.Embed(
            title=f"🔍 Google Search: {query}",
            description="Here are the top search results:",
            color=discord.Color.orange()
        )

        if not results.get("items"):
            embed.description = "No results found."
            return embed

        for i, item in enumerate(results["items"], start=1):
            title = item.get("title", "No Title")
            link = item.get("link", "")
            snippet = item.get("snippet", "No Description")

            embed.add_field(
                name=f"{i}. {title}",
                value=f"{snippet}\n[Link]({link})",
                inline=False
            )

        embed.set_footer(text="Powered by Google")
        return embed

    async def save_search_history(self, guild_id, user_id, query, result_count):
        record = {
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "query": query,
            "result_count": result_count,
            "timestamp": str(discord.utils.utcnow())
        }

        file = "search_history.json"
        try:
            if os.path.exists(file):
                with open(file, "r") as f:
                    history = json.load(f)
            else:
                history = {"searches": []}

            history["searches"].append(record)

            with open(file, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving search history: {e}")

    async def handle_search(self, ctx_or_inter, query, results):
        if not query:
            return await ctx_or_inter.send("⚠️ Please enter a search query.")

        results = max(1, min(5, results))

        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
            return await ctx_or_inter.send("❌ API credentials are missing.")

        async with ctx_or_inter.typing():
            data, error = await self.search_google(query, results)
            if error:
                return await ctx_or_inter.send(f"❌ {error}")

            embed = self.create_embed(query, data)

            await self.save_search_history(
                ctx_or_inter.guild.id if ctx_or_inter.guild else "DM",
                ctx_or_inter.author.id,
                query,
                results
            )

            await ctx_or_inter.send(embed=embed)

    @commands.command(name="gsearch")
    async def gsearch_prefix(self, ctx, *, query: str):
        """Search Google using a prefix command"""
        await self.handle_search(ctx, query, 3)

    @app_commands.command(name="googlesearch", description="Search Google (1–5 results)")
    @app_commands.describe(
        query="What do you want to search?",
        results="How many results to show (1–5)?"
    )
    async def googlesearch_slash(self, interaction: discord.Interaction, query: str, results: int = 3):
        """Slash command for Google search"""
        ctx = await self.bot.get_context(interaction)
        await self.handle_search(ctx, query, results)

    @googlesearch_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(f"⚠️ Something went wrong: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(GoogleSearchCog(bot))
    print("✅ Google Search cog loaded")
