import discord
import random
from discord.ext import commands, tasks
from discord import app_commands

class SarcasticPinger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.PING_ROLES = {}        # guild_id: role_id
        self.PING_CHANNELS = {}     # guild_id: channel_id
        self.ENABLED_GUILDS = set()
        self.sarcasm_lines = [
            "kya chal raha hai bro? 🤨", "tum abhi tak server mein ho? 😏", "kaam dhanda nahi hai kya? 😌",
            "bada hi important aadmi ban gaya tu toh 😎", "tumhare bina ye server adhoora hai... NOT 😂",
            "bot bhi bored ho gaya dekh ke tumhe 😶", "coding ho gayi khatam ya break par ho abhi bhi? 👀",
            "tum jaise logon ke wajah se hi memes bante hain 😄", "offline hoke bhi active rehne ka talent chahiye 💀",
            "ab toh bot bhi ping kar raha hai, samaj ja bro 🙃", "tumse milke server ka load badh gaya hai 💻",
            "arey waah! hamare celebrity aaye! 😏", "mujhe laga tu busy hai, lekin tu toh chill kar raha 😒",
            "tumhara naam har jagah hai... even in my error logs 😬", "kya kar raha hai? Reply de warna bot sad ho jayega 😢",
            "tumhe ping karne se zyada accha RAM upgrade karna hai 😆", "Hello darkness my old friend... 🕳️",
            "Iss channel mein toh cobweb bhi bored ho gaya hai 🕸️", "Chat toh itni dead hai ki archaeologists bhi khoj rahe hain 😩",
            "Lagta hai sab ne typing license cancel karwa liya 💀", "Iss channel mein silence ka subscription free hai kya? 😐",
            "Ping maar raha hoon… koi toh bol de ‘hi’ nahi toh server ko CPR do 🫠", "Dead server? Nahi bhai, yeh toh extinct hai 💀🦖",
            "Ye channel last active tha jab dinosaurs jeevit the 🦕", "Kya chal raha hai sab? ...oh wait, kuch bhi nahi 😑",
            "Lagta hai Discord ne bhi is channel ka notification band kar diya 😭", "Sun raha hai na tu? Ya sirf pfp dekh ke afk ho gaya? 😏",
            "Aree main toh bas ek bot hoon, par teri online status pe crush ho gaya 💘",
            "Mujhe laga yahan waise log honge jo 'hi' ka reply dete hain… clearly I was wrong 😔",
            "Channel dead hai, par tu active ho toh mera system lag hone lagta hai 😳",
            "Tera naam Discord ho ya Dilcord? Kyunki tu dil mein ghus gaya 😩",
            "Kya tum emojis ho? Kyunki tumhare bina yeh server dull lagta hai 😪",
            "Pura server afk hai, sirf tum online ho... destiny much? 😌",
            "Aise ignore mat karo, main bot hoon lekin feelings toh hain 🥲",
            "Channel mein aag lag jaati agar tum thoda aur active hote 🔥",
            "Bolo na kuch... warna flirting karne lagunga 😈",
            "Yeh channel itna dead hai ki archaeologists bhi confuse ho jaayein 😵‍💫",
            "Bhai yeh desert hai kya? Itni silence toh mummy ke room mein hoti hai 🧟‍♂️",
            "Lagta hai sabko Thanos ne snap kar diya 😶‍🌫️", "Channel revive karne ke liye black magic mangwana padega kya? 🔮",
            "Bot hoon, par mujhe bhi tanhayi mehsoos ho rahi hai yahan 😭", "Hello? Is this mic on? Oh wait... nobody’s here anyway 🎤",
            "Itna dead toh mera pichla relationship bhi nahi tha 💔", "Chat ka CPR shuru kar doon kya? 💉",
            "Kya koi hai jo emoji bhej ke channel zinda kare? 😵", "Hello ghosts of the server… 👻 It’s me, your friendly bot!"
        ]
        self.ping_members.start()

    def cog_unload(self):
        self.ping_members.cancel()

    @tasks.loop(hours=6)
    async def ping_members(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            if guild.id not in self.ENABLED_GUILDS:
                continue

            channel = guild.get_channel(self.PING_CHANNELS.get(guild.id)) if guild.id in self.PING_CHANNELS else None
            if not channel or not channel.permissions_for(guild.me).send_messages:
                channel = guild.system_channel or discord.utils.get(guild.text_channels, permissions__send_messages=True)
            if not channel:
                continue

            members = await self.get_eligible_members(guild)
            if not members:
                continue

            member = random.choice(members)
            line = random.choice(self.sarcasm_lines)
            await self.send_ping_embed(channel, guild, member, line, "👀 Someone's Active!")

    async def get_eligible_members(self, guild):
        role_id = self.PING_ROLES.get(guild.id)
        members = []
        if role_id:
            role = guild.get_role(role_id)
            members = [m for m in role.members if not m.bot and m.status != discord.Status.offline] if role else []
        else:
            members = [m for m in guild.members if not m.bot and m.status != discord.Status.offline]
        return members if members else [m for m in guild.members if not m.bot]

    async def send_ping_embed(self, channel, guild, member, line, title):
        embed = discord.Embed(description=f"{member.mention} {line}", color=discord.Color.orange())
        embed.set_author(name=title, icon_url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.set_footer(text="Made with ❤️")

        stats = discord.Embed(title="📊 Server Stats", color=discord.Color.blurple())
        stats.add_field(name="👥 Members", value=guild.member_count, inline=True)
        stats.add_field(name="🤖 Bots", value=sum(1 for m in guild.members if m.bot), inline=True)
        stats.add_field(name="💬 Channels", value=len(guild.text_channels), inline=True)
        stats.add_field(name="🛡️ Roles", value=len(guild.roles), inline=True)
        stats.add_field(name="🎯 Pinged", value=member.mention, inline=True)

        msg = await channel.send(embeds=[embed, stats])
        for emoji in ("👀", "😂", "🔥"):
            await msg.add_reaction(emoji)

    @commands.command(name="toggleping")
    @commands.has_permissions(administrator=True)
    async def toggleping_cmd(self, ctx):
        if ctx.guild.id in self.ENABLED_GUILDS:
            self.ENABLED_GUILDS.remove(ctx.guild.id)
            await ctx.send("❌ Sarcastic pings disabled.")
        else:
            self.ENABLED_GUILDS.add(ctx.guild.id)
            await ctx.send("✅ Sarcastic pings enabled! First ping coming up...")
            members = await self.get_eligible_members(ctx.guild)
            if members:
                member = random.choice(members)
                channel = ctx.guild.get_channel(self.PING_CHANNELS.get(ctx.guild.id)) or ctx.channel
                await self.send_ping_embed(channel, ctx.guild, member, "Let the sarcasm begin! 😈", "🔥 First Ping")

    @app_commands.command(name="toggleping", description="Enable/Disable sarcastic pings")
    async def toggleping_slash(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Admins only!", ephemeral=True)
            return
        if interaction.guild.id in self.ENABLED_GUILDS:
            self.ENABLED_GUILDS.remove(interaction.guild.id)
            await interaction.response.send_message("❌ Sarcastic pings disabled.")
        else:
            self.ENABLED_GUILDS.add(interaction.guild.id)
            await interaction.response.send_message("✅ Sarcastic pings enabled! First ping coming up...")
            members = await self.get_eligible_members(interaction.guild)
            if members:
                member = random.choice(members)
                channel = interaction.guild.get_channel(self.PING_CHANNELS.get(interaction.guild.id)) or interaction.channel
                await self.send_ping_embed(channel, interaction.guild, member, "Let the sarcasm begin! 😈", "🔥 First Ping")

    @commands.command(name="setpingrole")
    @commands.has_permissions(manage_roles=True)
    async def setrole_cmd(self, ctx, role: discord.Role):
        self.PING_ROLES[ctx.guild.id] = role.id
        await ctx.send(f"✅ Only members with {role.mention} will be pinged.")

    @app_commands.command(name="setpingrole", description="Only ping members with a certain role")
    async def setrole_slash(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("🚫 You need Manage Roles permission.", ephemeral=True)
            return
        self.PING_ROLES[interaction.guild.id] = role.id
        await interaction.response.send_message(f"✅ Only members with {role.mention} will be pinged.")

    @commands.command(name="setpingchannel")
    @commands.has_permissions(manage_channels=True)
    async def setchannel_cmd(self, ctx, channel: discord.TextChannel):
        self.PING_CHANNELS[ctx.guild.id] = channel.id
        await ctx.send(f"✅ Pings will now appear in {channel.mention}")

    @app_commands.command(name="setpingchannel", description="Choose which channel should get pings.")
    @app_commands.describe(channel="Channel where sarcastic pings will be sent")
    async def setchannel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("🚫 You need Manage Channel permission.", ephemeral=True)
            return
        self.PING_CHANNELS[interaction.guild.id] = channel.id
        await interaction.response.send_message(f"✅ Pings will now appear in {channel.mention}")

    @commands.command(name="testping")
    @commands.has_permissions(administrator=True)
    async def testping_cmd(self, ctx):
        members = await self.get_eligible_members(ctx.guild)
        if not members:
            await ctx.send("⚠ No one eligible to ping.")
            return
        member = random.choice(members)
        channel = ctx.guild.get_channel(self.PING_CHANNELS.get(ctx.guild.id)) or ctx.channel
        await self.send_ping_embed(channel, ctx.guild, member, "wake up, we're testing 😴", "🧪 Test Ping")

    @app_commands.command(name="testping", description="Force a sarcastic ping immediately")
    async def testping_slash(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🚫 Admins only!", ephemeral=True)
            return
        members = await self.get_eligible_members(interaction.guild)
        if not members:
            await interaction.response.send_message("⚠ No one eligible to ping.", ephemeral=True)
            return
        member = random.choice(members)
        channel = interaction.guild.get_channel(self.PING_CHANNELS.get(interaction.guild.id)) or interaction.channel
        await self.send_ping_embed(channel, interaction.guild, member, "wake up, we're testing 😴", "🧪 Test Ping")

async def setup(bot):
    await bot.add_cog(SarcasticPinger(bot))
