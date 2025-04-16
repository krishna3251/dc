import discord
from discord.ext import commands
import aiohttp
import json
import re
import urllib.parse
import asyncio
from typing import Optional, List, Dict, Any, Union
import os

class SearchCog(commands.Cog):
    """Search the web directly from Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        
        # API Keys - get from environment or use empty string
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "")
        self.google_cx = os.getenv("GOOGLE_CSE_ID", "")  
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")
        self.github_token = os.getenv("GITHUB_TOKEN", "")
    
    def cog_unload(self):
        """Clean up the aiohttp session when the cog is unloaded"""
        if self.session:
            self.bot.loop.create_task(self.session.close())
    
    async def make_request(self, url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make a request to the specified URL and return the JSON response"""
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"Status {response.status}: {response.reason}"}
        except Exception as e:
            return {"error": str(e)}
    
    def create_embed_pages(self, items: List[Dict[str, Any]], title: str, formatter) -> List[discord.Embed]:
        """Create paginated embeds from a list of items using the provided formatter function"""
        pages = []
        items_per_page = 5
        
        for i in range(0, len(items), items_per_page):
            page_items = items[i:i+items_per_page]
            
            embed = discord.Embed(
                title=title,
                description=formatter(page_items),
                color=0x3a9efa
            )
            
            page_num = i // items_per_page + 1
            total_pages = (len(items) + items_per_page - 1) // items_per_page
            embed.set_footer(text=f"Page {page_num}/{total_pages}")
            
            pages.append(embed)
        
        return pages
    
    @commands.command(name="google", aliases=["g"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def google(self, ctx, *, query: str):
        """Search Google for information"""
        if not self.google_api_key or not self.google_cx:
            await ctx.send("⚠️ Google search is not configured. Please set up API keys.")
            return
        
        # Indicate that the bot is searching
        async with ctx.typing():
            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            
            # Construct the API URL
            url = f"https://www.googleapis.com/customsearch/v1?key={self.google_api_key}&cx={self.google_cx}&q={encoded_query}"
            
            # Make the request
            result = await self.make_request(url)
            
            if "error" in result:
                await ctx.send(f"❌ Error: {result['error']}")
                return
            
            # Check if there are search results
            if "items" not in result or not result["items"]:
                await ctx.send(f"No results found for '{query}'")
                return
            
            # Format the results into an embed
            items = result["items"][:10]  # Limit to 10 results
            
            def format_results(items):
                return "\n\n".join([
                    f"**[{item.get('title', 'No Title')}]({item.get('link', '#')})**\n"
                    f"{item.get('snippet', 'No description available')}"
                    for item in items
                ])
            
            pages = self.create_embed_pages(
                items, 
                f"Google Search Results for '{query}'", 
                format_results
            )
            
            # If there's only one page, just send it
            if len(pages) == 1:
                await ctx.send(embed=pages[0])
                return
            
            # Otherwise, set up pagination
            current_page = 0
            message = await ctx.send(embed=pages[current_page])
            
            # Add navigation reactions
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    # Remove the user's reaction
                    try:
                        await message.remove_reaction(reaction, user)
                    except:
                        pass
                    
                    # Update the page based on the reaction
                    if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                    
                except asyncio.TimeoutError:
                    # Remove our reactions after timeout
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    break
    
    @commands.command(name="youtube", aliases=["yt"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def youtube(self, ctx, *, query: str):
        """Search YouTube for videos"""
        if not self.youtube_api_key:
            await ctx.send("⚠️ YouTube search is not configured. Please set up API keys.")
            return
        
        # Indicate that the bot is searching
        async with ctx.typing():
            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            
            # Construct the API URL
            url = f"https://www.googleapis.com/youtube/v3/search?key={self.youtube_api_key}&part=snippet&type=video&q={encoded_query}&maxResults=10"
            
            # Make the request
            result = await self.make_request(url)
            
            if "error" in result:
                await ctx.send(f"❌ Error: {result['error']}")
                return
            
            # Check if there are search results
            if "items" not in result or not result["items"]:
                await ctx.send(f"No YouTube videos found for '{query}'")
                return
            
            # Format the results into an embed
            items = result["items"]
            
            def format_results(items):
                return "\n\n".join([
                    f"**[{item['snippet'].get('title', 'No Title')}](https://www.youtube.com/watch?v={item['id']['videoId']})**\n"
                    f"👤 {item['snippet'].get('channelTitle', 'Unknown channel')} | "
                    f"📅 {item['snippet'].get('publishedAt', 'Unknown date')[:10]}\n"
                    f"{item['snippet'].get('description', 'No description available')}"
                    for item in items
                ])
            
            pages = self.create_embed_pages(
                items, 
                f"YouTube Search Results for '{query}'", 
                format_results
            )
            
            # If there's only one page, just send it
            if len(pages) == 1:
                await ctx.send(embed=pages[0])
                return
            
            # Otherwise, set up pagination
            current_page = 0
            message = await ctx.send(embed=pages[current_page])
            
            # Add navigation reactions
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    # Remove the user's reaction
                    try:
                        await message.remove_reaction(reaction, user)
                    except:
                        pass
                    
                    # Update the page based on the reaction
                    if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                    
                except asyncio.TimeoutError:
                    # Remove our reactions after timeout
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    break
    
    @commands.command(name="wikipedia", aliases=["wiki"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def wikipedia(self, ctx, *, query: str):
        """Search Wikipedia for information"""
        # Indicate that the bot is searching
        async with ctx.typing():
            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            
            # First search for articles
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json"
            
            # Make the request
            search_result = await self.make_request(search_url)
            
            if "error" in search_result:
                await ctx.send(f"❌ Error: {search_result['error']}")
                return
            
            # Check if there are search results
            if "query" not in search_result or "search" not in search_result["query"] or not search_result["query"]["search"]:
                await ctx.send(f"No Wikipedia articles found for '{query}'")
                return
            
            # Get the first result
            first_result = search_result["query"]["search"][0]
            page_id = first_result["pageid"]
            
            # Get the full content of the article
            content_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&pageids={page_id}&format=json"
            
            # Make the request
            content_result = await self.make_request(content_url)
            
            if "error" in content_result:
                await ctx.send(f"❌ Error: {content_result['error']}")
                return
            
            # Extract the article content
            try:
                page = content_result["query"]["pages"][str(page_id)]
                title = page["title"]
                extract = page["extract"]
                
                # Truncate if too long
                if len(extract) > 2000:
                    extract = extract[:1997] + "..."
                
                # Create embed
                embed = discord.Embed(
                    title=title,
                    url=f"https://en.wikipedia.org/?curid={page_id}",
                    description=extract,
                    color=0x3a9efa
                )
                
                embed.set_footer(text="Source: Wikipedia")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Failed to process Wikipedia article: {str(e)}")
    
    @commands.command(name="urban", aliases=["ud"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def urban_dictionary(self, ctx, *, query: str):
        """Look up a term on Urban Dictionary"""
        # Check if the channel is NSFW (Urban Dictionary can have mature content)
        if not isinstance(ctx.channel, discord.DMChannel) and not ctx.channel.is_nsfw():
            await ctx.send("⚠️ This command can only be used in NSFW channels due to potentially mature content.")
            return
        
        # Indicate that the bot is searching
        async with ctx.typing():
            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            
            # Construct the API URL
            url = f"https://api.urbandictionary.com/v0/define?term={encoded_query}"
            
            # Make the request
            result = await self.make_request(url)
            
            if "error" in result:
                await ctx.send(f"❌ Error: {result['error']}")
                return
            
            # Check if there are definitions
            if "list" not in result or not result["list"]:
                await ctx.send(f"No Urban Dictionary definitions found for '{query}'")
                return
            
            # Format the results into an embed
            definitions = result["list"]
            
            def format_results(defs):
                return "\n\n".join([
                    f"**Definition {i+1}:**\n"
                    f"{self.clean_definition(d['definition'])}\n\n"
                    f"**Example:**\n"
                    f"{self.clean_definition(d['example'])}\n\n"
                    f"👍 {d['thumbs_up']} | 👎 {d['thumbs_down']}"
                    for i, d in enumerate(defs)
                ])
            
            pages = self.create_embed_pages(
                definitions, 
                f"Urban Dictionary: {query}", 
                format_results
            )
            
            # Add the URL to the term
            for page in pages:
                page.add_field(
                    name="Link",
                    value=f"[View on Urban Dictionary](https://www.urbandictionary.com/define.php?term={encoded_query})",
                    inline=False
                )
            
            # If there's only one page, just send it
            if len(pages) == 1:
                await ctx.send(embed=pages[0])
                return
            
            # Otherwise, set up pagination
            current_page = 0
            message = await ctx.send(embed=pages[current_page])
            
            # Add navigation reactions
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    # Remove the user's reaction
                    try:
                        await message.remove_reaction(reaction, user)
                    except:
                        pass
                    
                    # Update the page based on the reaction
                    if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                    
                except asyncio.TimeoutError:
                    # Remove our reactions after timeout
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    break
    
    def clean_definition(self, text: str) -> str:
        """Clean up Urban Dictionary formatting"""
        # Replace [bracketed] terms with italicized text
        text = re.sub(r'\[(.*?)\]', r'*\1*', text)
        
        # Truncate if too long
        if len(text) > 1000:
            text = text[:997] + "..."
            
        return text
    
    @commands.command(name="github", aliases=["gh"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def github(self, ctx, *, query: str):
        """Search GitHub repositories"""
        # Indicate that the bot is searching
        async with ctx.typing():
            # URL encode the query
            encoded_query = urllib.parse.quote(query)
            
            # Construct the API URL
            url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc"
            
            # Set up headers
            headers = {}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Make the request
            result = await self.make_request(url, headers)
            
            if "error" in result:
                await ctx.send(f"❌ Error: {result['error']}")
                return
            
            # Check if there are search results
            if "items" not in result or not result["items"]:
                await ctx.send(f"No GitHub repositories found for '{query}'")
                return
            
            # Format the results into an embed
            repos = result["items"][:10]  # Limit to 10 results
            
            def format_results(repos):
                return "\n\n".join([
                    f"**[{repo['full_name']}]({repo['html_url']})**\n"
                    f"{repo.get('description', 'No description available')}\n"
                    f"⭐ {repo['stargazers_count']} | 🍴 {repo['forks_count']} | "
                    f"🔤 {repo['language'] or 'Unknown'} | "
                    f"📅 Updated: {repo['updated_at'][:10]}"
                    for repo in repos
                ])
            
            pages = self.create_embed_pages(
                repos, 
                f"GitHub Search Results for '{query}'", 
                format_results
            )
            
            # If there's only one page, just send it
            if len(pages) == 1:
                await ctx.send(embed=pages[0])
                return
            
            # Otherwise, set up pagination
            current_page = 0
            message = await ctx.send(embed=pages[current_page])
            
            # Add navigation reactions
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    # Remove the user's reaction
                    try:
                        await message.remove_reaction(reaction, user)
                    except:
                        pass
                    
                    # Update the page based on the reaction
                    if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                    
                except asyncio.TimeoutError:
                    # Remove our reactions after timeout
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    break
    
    @commands.command(name="weather")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def weather(self, ctx, *, location: str):
        """Check the current weather for a location"""
        # Get the OpenWeatherMap API key
        api_key = os.getenv("OPENWEATHER_API_KEY", "")
        
        if not api_key:
            await ctx.send("⚠️ Weather search is not configured. Please set up API keys.")
            return
        
        # Indicate that the bot is searching
        async with ctx.typing():
            # URL encode the location
            encoded_location = urllib.parse.quote(location)
            
            # Construct the API URL
            url = f"http://api.openweathermap.org/data/2.5/weather?q={encoded_location}&appid={api_key}&units=metric"
            
            # Make the request
            result = await self.make_request(url)
            
            if "error" in result:
                await ctx.send(f"❌ Error: {result['error']}")
                return
            
            # Check if the request was successful
            if result.get("cod") != 200:
                await ctx.send(f"❌ Error: {result.get('message', 'Unknown error')}")
                return
            
            # Extract weather information
            city_name = result["name"]
            country = result["sys"]["country"]
            
            temp = result["main"]["temp"]
            temp_feels = result["main"]["feels_like"]
            humidity = result["main"]["humidity"]
            wind_speed = result["wind"]["speed"]
            
            weather_main = result["weather"][0]["main"]
            weather_description = result["weather"][0]["description"].capitalize()
            weather_icon = result["weather"][0]["icon"]
            
            # Get the corresponding weather emoji
            weather_emojis = {
                "Clear": "☀️",
                "Clouds": "☁️",
                "Rain": "🌧️",
                "Drizzle": "🌦️",
                "Thunderstorm": "⛈️",
                "Snow": "❄️",
                "Mist": "🌫️",
                "Fog": "🌫️",
                "Haze": "🌫️",
                "Dust": "🌫️",
                "Smoke": "🌫️",
                "Tornado": "🌪️"
            }
            
            weather_emoji = weather_emojis.get(weather_main, "🌡️")
            
            # Create the embed
            embed = discord.Embed(
                title=f"Weather for {city_name}, {country}",
                description=f"{weather_emoji} **{weather_description}**",
                color=0x3a9efa,
                timestamp=ctx.message.created_at
            )
            
            # Add weather info fields
            embed.add_field(name="Temperature", value=f"🌡️ {temp}°C (Feels like: {temp_feels}°C)", inline=False)
            embed.add_field(name="Humidity", value=f"💧 {humidity}%", inline=True)
            embed.add_field(name="Wind Speed", value=f"💨 {wind_speed} m/s", inline=True)
            
            # Add weather icon
            embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{weather_icon}@2x.png")
            
            # Add footer
            embed.set_footer(text="Powered by OpenWeatherMap")
            
            await ctx.send(embed=embed)
    
    @commands.command(name="searchhelp")
    async def searchhelp(self, ctx):
        """Show help for all search commands"""
        embed = discord.Embed(
            title="🔍 Search Command Help",
            description="Here are all the available search commands:",
            color=0x3a9efa
        )
        
        embed.add_field(
            name=f"{ctx.prefix}google [query]",
            value="Search Google for information",
            inline=False
        )
        
        embed.add_field(
            name=f"{ctx.prefix}youtube [query]",
            value="Search YouTube for videos",
            inline=False
        )
        
        embed.add_field(
            name=f"{ctx.prefix}wikipedia [query]",
            value="Search Wikipedia for articles",
            inline=False
        )
        
        embed.add_field(
            name=f"{ctx.prefix}urban [query]",
            value="Look up a term on Urban Dictionary (NSFW channels only)",
            inline=False
        )
        
        embed.add_field(
            name=f"{ctx.prefix}github [query]",
            value="Search GitHub for repositories",
            inline=False
        )
        
        embed.add_field(
            name=f"{ctx.prefix}weather [location]",
            value="Get current weather information for a location",
            inline=False
        )
        
        embed.set_footer(text="All search commands have a cooldown to prevent API abuse")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SearchCog(bot))
