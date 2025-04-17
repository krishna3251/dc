import discord
from discord.ext import commands
import time
from db_handler import DatabaseHandler

class AntiSpamCog(commands.Cog):
    """🛑 Anti-Spam System - Detects and removes mention spamming with performance optimization."""

    def __init__(self, bot):
        self.bot = bot
        self.default_mention_limit = 3   # Default max allowed mentions per message
        
        # Server-specific settings
        self.server_settings = {}
        
        # Message cooldown tracking for rate limiting
        self.user_last_message = {}  # {user_id: last_message_timestamp}
        self.cooldown_seconds = 0.8  # Minimum seconds between messages

    def get_mention_limit(self, guild_id):
        """Get the mention limit for a specific guild with caching"""
        if guild_id in self.server_settings:
            return self.server_settings[guild_id].get('mention_limit', self.default_mention_limit)
            
        try:
            guild = DatabaseHandler.get_guild_settings(guild_id)
            if guild:
                limit = getattr(guild, 'mention_limit', self.default_mention_limit)
                if guild_id not in self.server_settings:
                    self.server_settings[guild_id] = {}
                self.server_settings[guild_id]['mention_limit'] = limit
                return limit
        except Exception as e:
            print(f"Error getting mention limit: {e}")
            
        return self.default_mention_limit

    @commands.Cog.listener()
    async def on_message(self, message):
        """Optimized spam detection with improved performance."""
        if message.author.bot or not message.guild:
            return  # Ignore bot messages and DMs
            
        user_id = message.author.id
        current_time = time.time()
        
        if user_id in self.user_last_message:
            time_diff = current_time - self.user_last_message[user_id]
            if time_diff < self.cooldown_seconds:
                self.user_last_message[user_id] = current_time
                return
                
        self.user_last_message[user_id] = current_time
        
        mention_limit = self.get_mention_limit(message.guild.id)

        # Detect Mention Spamming
        if len(message.mentions) > mention_limit:
            try:
                await message.delete()
                await message.channel.send(
                    f"🚫 {message.author.mention}, please do not mention too many users!",
                    delete_after=5.0
                )
            except discord.errors.NotFound:
                pass
            except discord.errors.Forbidden:
                pass

    @commands.command(name="setmentionlimit", help="⚙️ Set the max allowed mentions per message.")
    @commands.has_permissions(administrator=True)
    async def set_mention_limit(self, ctx, limit: int):
        """Allows admins to set mention spam limit with database persistence."""
        if limit < 0:
            await ctx.send("❌ Mention limit cannot be negative!")
            return
            
        guild_id = ctx.guild.id
        if guild_id not in self.server_settings:
            self.server_settings[guild_id] = {}
        self.server_settings[guild_id]['mention_limit'] = limit
        
        DatabaseHandler.update_guild_settings(guild_id, mention_limit=limit)
        
        await ctx.send(f"✅ Mention spam limit set to {limit}!")

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))
    print("✅ AntiSpamCog cog loaded!")
