import discord
from discord.ext import commands
import re

class AntiSpamCog(commands.Cog):
    """🛑 Anti-Spam System - Detects and removes mention/link spamming."""

    def __init__(self, bot):
        self.bot = bot
        self.mention_limit = 3   # Max allowed mentions per message
        self.link_patterns = [
            r"https?://[^\s]+",  # General links (http/https)
            r"discord\.gg/[^\s]+",  # Discord invite links
            r"store\.steampowered\.com/[^\s]+",  # Steam store links
            r"twitch\.tv/[^\s]+",  # Twitch links
        ]

    @commands.Cog.listener()
    async def on_message(self, message):
        """Detects and removes spam messages."""
        if message.author.bot:
            return  # Ignore bot messages

        # Detect Mention Spamming
        if len(message.mentions) > self.mention_limit:
            await message.delete()
            await message.channel.send(f"🚫 {message.author.mention}, please do not mention too many users!")
            return

        # Detect Link Spamming
        for pattern in self.link_patterns:
            if re.search(pattern, message.content):
                await message.delete()
                await message.channel.send(f"🚫 {message.author.mention}, sending links is not allowed!")
                return

    @commands.command(name="setmentionlimit", help="⚙️ Set the max allowed mentions per message.")
    @commands.has_permissions(administrator=True)
    async def set_mention_limit(self, ctx, limit: int):
        """Allows admins to set mention spam limit."""
        self.mention_limit = limit
        await ctx.send(f"✅ Mention spam limit set to {limit}!")

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))
    print("✅ AntiSpamCog cog loaded!")
