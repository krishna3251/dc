import discord
from discord.ext import commands
import re
import time
from db_handler import DatabaseHandler

class AntiSpamCog(commands.Cog):
    """🛑 Anti-Spam System - Detects and removes mention/link spamming with performance optimization."""

    def __init__(self, bot):
        self.bot = bot
        self.default_mention_limit = 3   # Default max allowed mentions per message
        
        # Create a dictionary for server-specific settings
        self.server_settings = {}
        
        # Compile regex patterns once for better performance
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in [
                r"https?://[^\s]+",  # General links (http/https)
                r"discord\.gg/[^\s]+",  # Discord invite links
                r"store\.steampowered\.com/[^\s]+",  # Steam store links
                r"twitch\.tv/[^\s]+",  # Twitch links
            ]
        ]
        
        # Message cooldown tracking for rate limiting
        self.user_last_message = {}  # {user_id: last_message_timestamp}
        self.cooldown_seconds = 0.8  # Minimum seconds between messages
        
        # Cache white-listed channels
        self.whitelisted_channels = set()  # Channels where link posting is allowed

    def get_mention_limit(self, guild_id):
        """Get the mention limit for a specific guild with caching"""
        # First check in-memory cache for fastest access
        if guild_id in self.server_settings:
            return self.server_settings[guild_id].get('mention_limit', self.default_mention_limit)
            
        try:
            # Get fresh data from database
            guild = DatabaseHandler.get_guild_settings(guild_id)
            if guild:
                # Extract the limit value - don't keep the SQLAlchemy object in memory
                limit = getattr(guild, 'mention_limit', self.default_mention_limit)
                
                # Update cache with just the value, not the SQLAlchemy object
                if guild_id not in self.server_settings:
                    self.server_settings[guild_id] = {}
                self.server_settings[guild_id]['mention_limit'] = limit
                return limit
        except Exception as e:
            print(f"Error getting mention limit: {e}")
            
        # Fallback to default if any issue occurs
        return self.default_mention_limit

    @commands.Cog.listener()
    async def on_message(self, message):
        """Optimized spam detection with improved performance."""
        # Quick exit checks
        if message.author.bot or not message.guild:
            return  # Ignore bot messages and DMs
            
        # Skip messages in whitelisted channels
        if message.channel.id in self.whitelisted_channels:
            return
            
        # Check for rate limiting (prevent message spam)
        user_id = message.author.id
        current_time = time.time()
        
        if user_id in self.user_last_message:
            time_diff = current_time - self.user_last_message[user_id]
            if time_diff < self.cooldown_seconds:
                # Message is too soon after previous one - potential spam
                # We won't delete it, but we'll update the timestamp for tracking
                self.user_last_message[user_id] = current_time
                return
                
        # Update last message timestamp
        self.user_last_message[user_id] = current_time
        
        # Get guild-specific mention limit
        mention_limit = self.get_mention_limit(message.guild.id)

        # Detect Mention Spamming - this is fast, check first
        if len(message.mentions) > mention_limit:
            try:
                await message.delete()
                await message.channel.send(
                    f"🚫 {message.author.mention}, please do not mention too many users!",
                    delete_after=5.0  # Auto-delete after 5 seconds for cleaner channels
                )
            except discord.errors.NotFound:
                pass  # Message already deleted
            except discord.errors.Forbidden:
                pass  # No permission to delete
            return

        # Detect Link Spamming only if the message might contain links (fast check first)
        if "http" in message.content or "www." in message.content or ".com" in message.content:
            for pattern in self.compiled_patterns:
                if pattern.search(message.content):
                    try:
                        await message.delete()
                        await message.channel.send(
                            f"🚫 {message.author.mention}, sending links is not allowed!",
                            delete_after=5.0  # Auto-delete after 5 seconds
                        )
                    except discord.errors.NotFound:
                        pass  # Message already deleted
                    except discord.errors.Forbidden:
                        pass  # No permission to delete
                    return

    @commands.command(name="setmentionlimit", help="⚙️ Set the max allowed mentions per message.")
    @commands.has_permissions(administrator=True)
    async def set_mention_limit(self, ctx, limit: int):
        """Allows admins to set mention spam limit with database persistence."""
        if limit < 0:
            await ctx.send("❌ Mention limit cannot be negative!")
            return
            
        # Update in memory
        guild_id = ctx.guild.id
        if guild_id not in self.server_settings:
            self.server_settings[guild_id] = {}
        self.server_settings[guild_id]['mention_limit'] = limit
        
        # Update in database
        DatabaseHandler.update_guild_settings(guild_id, mention_limit=limit)
        
        await ctx.send(f"✅ Mention spam limit set to {limit}!")
        
    @commands.command(name="whitelist", help="⚙️ Whitelist a channel to allow links.")
    @commands.has_permissions(administrator=True)
    async def whitelist_channel(self, ctx, channel: discord.TextChannel = None):
        """Whitelist a channel to allow link posting."""
        channel = channel or ctx.channel
        self.whitelisted_channels.add(channel.id)
        await ctx.send(f"✅ Links are now allowed in {channel.mention}!")

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))
    print("✅ AntiSpamCog cog loaded!")
