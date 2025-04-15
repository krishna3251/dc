import discord
import random
from discord.ext import commands, tasks
from discord import app_commands

class SarcasticPinger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.PING_CHANNELS = {}  # guild_id: channel_id
        self.ENABLED_GUILDS = set()
        self.animal_gifs = [
            "https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif",
            "https://media.giphy.com/media/mlvseq9yvZhba/giphy.gif",
            "https://media.giphy.com/media/3oriO0OEd9QIDdllqo/giphy.gif",
            "https://media.giphy.com/media/OmK8lulOMQ9XO/giphy.gif",
            "https://media.giphy.com/media/12HZukMBlutpoQ/giphy.gif"
        ]
        self.sarcasm_lines = [
            "kya chal raha hai bro? 🨨", "tum abhi tak server mein ho? 😏", "kaam dhanda nahi hai kya? 😌",
            "Hello ghosts of the server… 👻 It’s me, your friendly bot!"
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

            channel_id = self.PING_CHANNELS.get(guild.id)
            channel = guild.get_channel(channel_id) if channel_id else guild.system_channel
            if not channel or not channel.permissions_for(guild.me).send_messages:
                continue

            members = await self.get_eligible_members(guild)
            if not members:
                continue

            member = random.choice(members)
            line = random.choice(self.sarcasm_lines)
            gif = random.choice(self.animal_gifs)
            await self.send_ping_embed(channel, guild, member, line, "👀 Someone's Active!", gif)

    async def get_eligible_members(self, guild):
        members = [m for m in guild.members if not m.bot and (m.status != discord.Status.offline)]
        return members if members else [m for m in guild.members if not m.bot]

    async def send_ping_embed(self, channel, guild, member, line, title, gif_url):
        embed = discord.Embed(description=f"{member.mention} {line}", color=discord.Color.orange())
        embed.set_author(name=title, icon_url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.set_footer(text="Made with ❤️")
        embed.set_image(url=gif_url)

        stats = discord.Embed(title="📊 Server Stats", color=discord.Color.blurple())
        stats.add_field(name="👥 Members", value=guild.member_count, inline=True)
        stats.add_field(name="🤖 Bots", value=sum(1 for m in guild.members if m.bot), inline=True)
        stats.add_field(name="💬 Channels", value=len(guild.text_channels), inline=True)
        stats.add_field(name="🛡️ Roles", value=len(guild.roles), inline=True)
        stats.add_field(name="🎯 Pinged", value=member.mention, inline=True)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="More Sarcasm", style=discord.ButtonStyle.secondary))
        view.add_item(discord.ui.Button(label="Revive Chat", style=discord.ButtonStyle.success))

        msg = await channel.send(embeds=[embed, stats], view=view)
        for emoji in ("👀", "😂", "🔥"):
            await msg.add_reaction(emoji)

    # SLASH COMMANDS BELOW

    @app_commands.command(name="setpingchannel", description="Set this channel for sarcastic pings")
    async def set_ping_channel(self, interaction: discord.Interaction):
        self.PING_CHANNELS[interaction.guild_id] = interaction.channel_id
        await interaction.response.send_message("✅ Ping channel set!", ephemeral=True)

    @app_commands.command(name="toggleping", description="Enable/Disable sarcastic pings")
    async def toggle_ping(self, interaction: discord.Interaction):
        gid = interaction.guild_id
        if gid in self.ENABLED_GUILDS:
            self.ENABLED_GUILDS.remove(gid)
            await interaction.response.send_message("🔕 Sarcastic pings disabled.", ephemeral=True)
        else:
            self.ENABLED_GUILDS.add(gid)
            await interaction.response.send_message("🔔 Sarcastic pings enabled.", ephemeral=True)

    @app_commands.command(name="testping", description="Trigger a test sarcastic ping")
    async def test_ping(self, interaction: discord.Interaction):
        guild = interaction.guild
        members = await self.get_eligible_members(guild)
        if not members:
            await interaction.response.send_message("😢 No eligible members to ping.", ephemeral=True)
            return
        member = random.choice(members)
        gif = random.choice(self.animal_gifs)
        line = random.choice(self.sarcasm_lines)
        await self.send_ping_embed(interaction.channel, guild, member, line, "🔁 Test Ping", gif)
        await interaction.response.send_message("📨 Test ping sent!", ephemeral=True)

    async def cog_load(self):
        self.bot.tree.add_command(self.set_ping_channel)
        self.bot.tree.add_command(self.toggle_ping)
        self.bot.tree.add_command(self.test_ping)

        try:
            synced = await self.bot.tree.sync()
            print(f"✅ Synced {len(synced)} command(s) for sarcastic pinger.")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SarcasticPinger(bot))
