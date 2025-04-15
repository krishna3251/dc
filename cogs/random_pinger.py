import discord
import random
import aiohttp
import os
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")  # Make sure this is set in your .env

# Guild configuration toggle (defaults ON)
ENABLED_GUILDS = set()

class RandomPinger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sarcasm_lines = [
            "kya chal raha hai bro? 🤨",
            "tum abhi tak server mein ho? 😏",
            "kaam dhanda nahi hai kya? 😌",
            "bada hi important aadmi ban gaya tu toh 😎",
            "tumhare bina ye server adhoora hai... NOT 😂",
            "bot bhi bored ho gaya dekh ke tumhe 😶",
            "coding ho gayi khatam ya break par ho abhi bhi? 👀",
            "tum jaise logon ke wajah se hi memes bante hain 😄",
            "offline hoke bhi active rehne ka talent chahiye 💀",
            "ab toh bot bhi ping kar raha hai, samaj ja bro 🙃",
            "tumse milke server ka load badh gaya hai 💻",
            "arey waah! hamare celebrity aaye! 😏",
            "mujhe laga tu busy hai, lekin tu toh chill kar raha 😒",
            "tumhara naam har jagah hai... even in my error logs 😬",
            "kya kar raha hai? Reply de warna bot sad ho jayega 😢",
            "tumhe ping karne se zyada accha RAM upgrade karna hai 😆"
        ]
        self.ping_members.start()

    def cog_unload(self):
        self.ping_members.cancel()

    async def get_random_gif(self, search_term="funny animals"):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.giphy.com/v1/gifs/search",
                    params={"api_key": GIPHY_API_KEY, "q": search_term, "limit": 25, "rating": "pg"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("data", [])
                        if results:
                            gif_url = random.choice(results).get("images", {}).get("original", {}).get("url")
                            return gif_url
        except:
            pass
        return None

    @tasks.loop(hours=6)
    async def ping_members(self):
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            if guild.id not in ENABLED_GUILDS:
                continue

            text_channels = [ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages]
            if not text_channels:
                continue
            channel = random.choice(text_channels)

            members = [m for m in guild.members if not m.bot and m.status != discord.Status.offline]
            if not members:
                continue
            member = random.choice(members)

            message = random.choice(self.sarcasm_lines)
            gif_url = await self.get_random_gif()

            embed = discord.Embed(
                title="👀 Someone's Active!",
                description=f"{member.mention} {message}",
                color=discord.Color.random()
            )
            if gif_url:
                embed.set_image(url=gif_url)

            await channel.send(embed=embed)

    @commands.command(name="toggleping", help="Enable/Disable sarcastic pings in this server.")
    @commands.has_permissions(administrator=True)
    async def toggle_pinger(self, ctx):
        if ctx.guild.id in ENABLED_GUILDS:
            ENABLED_GUILDS.remove(ctx.guild.id)
            await ctx.send("❌ Sarcastic pings disabled for this server.")
        else:
            ENABLED_GUILDS.add(ctx.guild.id)
            await ctx.send("✅ Sarcastic pings enabled for this server.")

async def setup(bot):
    await bot.add_cog(RandomPinger(bot))
