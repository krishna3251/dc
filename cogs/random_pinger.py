import discord
import random
import aiohttp
import os
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")  # Make sure this is set in your .env

# Guild configuration
ENABLED_GUILDS = set()
PING_CHANNELS = {}  # guild_id: channel_id

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
            "Hello darkness my old friend... 🕳️"
            "Iss channel mein toh cobweb bhi bored ho gaya hai 🕸️"
            "Chat toh itni dead hai ki archaeologists bhi khoj rahe hain 😩"
            "Lagta hai sab ne typing license cancel karwa liya 💀"
            "Iss channel mein silence ka subscription free hai kya? 😐"
            "Ping maar raha hoon… koi toh bol de ‘hi’ nahi toh server ko CPR do 🫠"
            "Dead server? Nahi bhai, yeh toh extinct hai 💀🦖"
            "Ye channel last active tha jab dinosaurs jeevit the 🦕"
            "Kya chal raha hai sab? ...oh wait, kuch bhi nahi 😑"
            "Lagta hai Discord ne bhi is channel ka notification band kar diya 😭"
            "Sun raha hai na tu? Ya sirf pfp dekh ke afk ho gaya? 😏"
            "Aree main toh bas ek bot hoon, par teri online status pe crush ho gaya 💘"
            "Mujhe laga yahan waise log honge jo 'hi' ka reply dete hain… clearly I was wrong 😔"
            "Channel dead hai, par tu active ho toh mera system lag hone lagta hai 😳"
            "Tera naam Discord ho ya Dilcord? Kyunki tu dil mein ghus gaya 😩"
            "Kya tum emojis ho? Kyunki tumhare bina yeh server dull lagta hai 😪"
            "Pura server afk hai, sirf tum online ho... destiny much? 😌"
            "Aise ignore mat karo, main bot hoon lekin feelings toh hain 🥲"
            "Channel mein aag lag jaati agar tum thoda aur active hote 🔥"
            "Bolo na kuch... warna flirting karne lagunga 😈"
            "Yeh channel itna dead hai ki archaeologists bhi confuse ho jaayein 😵‍💫"
            "Bhai yeh desert hai kya? Itni silence toh mummy ke room mein hoti hai 🧟‍♂️"
            "Lagta hai sabko Thanos ne snap kar diya 😶‍🌫️"
            "Channel revive karne ke liye black magic mangwana padega kya? 🔮"
            "Bot hoon, par mujhe bhi tanhayi mehsoos ho rahi hai yahan 😭"
            "Hello? Is this mic on? Oh wait... nobody’s here anyway 🎤"
            "Itna dead toh mera pichla relationship bhi nahi tha 💔"
            "Chat ka CPR shuru kar doon kya? 💉"
            "Kya koi hai jo emoji bhej ke channel zinda kare? 😵"
            "Hello ghosts of the server… 👻 It’s me, your friendly bot!"
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

            channel = None
            if guild.id in PING_CHANNELS:
                channel = guild.get_channel(PING_CHANNELS[guild.id])

            if not channel or not channel.permissions_for(guild.me).send_messages:
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

    @app_commands.command(name="toggleping", description="Enable/Disable sarcastic pings in this server.")
    async def slash_toggle_pinger(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return

        if interaction.guild.id in ENABLED_GUILDS:
            ENABLED_GUILDS.remove(interaction.guild.id)
            await interaction.response.send_message("❌ ping chalu nhi hoga kuch to gadbad hai .")
        else:
            ENABLED_GUILDS.add(interaction.guild.id)
            await interaction.response.send_message("✅ ping chalu ho gya malik")

    @commands.command(name="setpingchannel", help="Set the channel where sarcasm pings should appear.")
    @commands.has_permissions(manage_channels=True)
    async def set_ping_channel(self, ctx, channel: discord.TextChannel):
        PING_CHANNELS[ctx.guild.id] = channel.id
        ENABLED_GUILDS.add(ctx.guild.id)
        await ctx.send(f"✅ Sarcastic pings will now appear in {channel.mention}")

    @app_commands.command(name="setpingchannel", description="Set the channel where sarcasm pings should appear.")
    async def slash_set_ping_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("You need manage channel permissions to use this command.", ephemeral=True)
            return

        PING_CHANNELS[interaction.guild.id] = channel.id
        ENABLED_GUILDS.add(interaction.guild.id)
        await interaction.response.send_message(f"✅ Sarcastic pings will now appear in {channel.mention}")

    @commands.command(name="testping", help="Force a test sarcastic ping now.")
    @commands.has_permissions(administrator=True)
    async def test_ping(self, ctx):
        members = [m for m in ctx.guild.members if not m.bot and m.status != discord.Status.offline]
        if not members:
            await ctx.send("⚠ No eligible members found for test ping.")
            return

        member = random.choice(members)
        message = random.choice(self.sarcasm_lines)
        gif_url = await self.get_random_gif()

        embed = discord.Embed(
            title="🧪 Test Ping",
            description=f"{member.mention} {message}",
            color=discord.Color.random()
        )
        if gif_url:
            embed.set_image(url=gif_url)

        await ctx.send(embed=embed)

    @app_commands.command(name="testping", description="Force a test sarcastic ping now.")
    async def slash_test_ping(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return

        members = [m for m in interaction.guild.members if not m.bot and m.status != discord.Status.offline]
        if not members:
            await interaction.response.send_message("⚠ No eligible members found for test ping.", ephemeral=True)
            return

        member = random.choice(members)
        message = random.choice(self.sarcasm_lines)
        gif_url = await self.get_random_gif()

        embed = discord.Embed(
            title="🧪 Test Ping",
            description=f"{member.mention} {message}",
            color=discord.Color.random()
        )
        if gif_url:
            embed.set_image(url=gif_url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(RandomPinger(bot))
