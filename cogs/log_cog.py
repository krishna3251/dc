import discord
from discord.ext import commands
import datetime
import json
import os
import asyncio
from typing import Optional, Union, Dict, Any
from discord import app_commands

class LoggingCog(commands.Cog):
    """Advanced server logging system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logs_directory = os.path.join("data", "logs")
        self.settings_path = os.path.join("data", "logs", "settings.json")
        self.enabled_guilds = {}
        self.ensure_directories()
        self.load_settings()
        
    def ensure_directories(self):
        """Ensure the logs directory exists"""
        os.makedirs(self.logs_directory, exist_ok=True)
    
    def load_settings(self):
        """Load logging settings from the settings file"""
        if not os.path.exists(self.settings_path):
            # Create default settings file
            self.save_settings()
            return
        
        try:
            with open(self.settings_path, 'r') as f:
                self.enabled_guilds = json.load(f)
        except Exception as e:
            print(f"Error loading logging settings: {e}")
            self.enabled_guilds = {}
    
    def save_settings(self):
        """Save logging settings to the settings file"""
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.enabled_guilds, f, indent=4)
        except Exception as e:
            print(f"Error saving logging settings: {e}")
    
    def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get settings for a specific guild"""
        guild_id = str(guild_id)
        if guild_id not in self.enabled_guilds:
            # Use default settings from config
            from config import DEFAULT_LOGGING_SETTINGS
            self.enabled_guilds[guild_id] = DEFAULT_LOGGING_SETTINGS.copy()
            self.save_settings()
        
        return self.enabled_guilds[guild_id]
    
    def update_guild_settings(self, guild_id: int, settings: Dict[str, Any]):
        """Update settings for a specific guild"""
        guild_id = str(guild_id)
        self.enabled_guilds[guild_id] = settings
        self.save_settings()
    
    def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get the configured log channel for a guild"""
        settings = self.get_guild_settings(guild.id)
        
        # Return None if logging is disabled
        if not settings.get("enabled", False):
            return None
        
        # Get the log channel ID
        log_channel_id = settings.get("log_channel")
        if not log_channel_id:
            return None
        
        # Get the channel object
        channel = guild.get_channel(int(log_channel_id))
        return channel if isinstance(channel, discord.TextChannel) else None
    
    async def log_event(self, guild: discord.Guild, embed: discord.Embed, event_type: str = None):
        """Log an event to the configured log channel"""
        # Check if logging is enabled for this event type
        settings = self.get_guild_settings(guild.id)
        if not settings.get("enabled", False):
            return
        
        # If event_type is specified, check if it's enabled
        if event_type and not settings.get(f"log_{event_type}", True):
            return
        
        # Get the log channel
        log_channel = self.get_log_channel(guild)
        if not log_channel:
            return
        
        # Set footer with timestamp
        embed.timestamp = datetime.datetime.utcnow()
        
        # Log the event
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            # We don't have permission to send messages
            pass
        except discord.HTTPException as e:
            print(f"Error sending log message: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when a member joins the server"""
        guild = member.guild
        
        # Create embed
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} joined the server",
            color=discord.Color.green()
        )
        
        # Add member information
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add account creation date
        created_at = int(member.created_at.timestamp())
        embed.add_field(
            name="Account Created", 
            value=f"<t:{created_at}:F> (<t:{created_at}:R>)",
            inline=False
        )
        
        # Add account age
        account_age = (datetime.datetime.utcnow() - member.created_at).days
        embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
        
        # Add member count
        embed.add_field(name="Member Count", value=str(guild.member_count), inline=True)
        
        # Add member ID
        embed.set_footer(text=f"User ID: {member.id}")
        
        # Log the event
        await self.log_event(guild, embed, "member_join")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when a member leaves the server"""
        guild = member.guild
        
        # Create embed
        embed = discord.Embed(
            title="Member Left",
            description=f"{member.mention} left the server",
            color=discord.Color.red()
        )
        
        # Add member information
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add join date if available
        if member.joined_at:
            joined_at = int(member.joined_at.timestamp())
            embed.add_field(
                name="Joined Server", 
                value=f"<t:{joined_at}:F> (<t:{joined_at}:R>)",
                inline=False
            )
            
            # Add time spent on server
            time_on_server = (datetime.datetime.utcnow() - member.joined_at).days
            embed.add_field(name="Time on Server", value=f"{time_on_server} days", inline=True)
        
        # Add roles
        if len(member.roles) > 1:  # Exclude @everyone
            roles = [role.mention for role in member.roles if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "None"
            embed.add_field(name="Roles", value=roles_str, inline=False)
        
        # Add new member count
        embed.add_field(name="Member Count", value=str(guild.member_count), inline=True)
        
        # Add member ID
        embed.set_footer(text=f"User ID: {member.id}")
        
        # Log the event
        await self.log_event(guild, embed, "member_leave")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log when a member is updated"""
        # Only log if there's a change we care about
        guild = after.guild
        
        # Check for nickname changes
        if before.nick != after.nick:
            embed = discord.Embed(
                title="Nickname Changed",
                color=discord.Color.blue()
            )
            
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=after.display_avatar.url)
            
            embed.add_field(name="Before", value=before.nick or after.name, inline=True)
            embed.add_field(name="After", value=after.nick or after.name, inline=True)
            
            embed.set_footer(text=f"User ID: {after.id}")
            
            await self.log_event(guild, embed, "member_update")
        
        # Check for role changes
        if before.roles != after.roles:
            # Figure out which roles were added and which were removed
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles:
                embed = discord.Embed(
                    title="Roles Added",
                    description=f"{after.mention} was given {len(added_roles)} role(s)",
                    color=discord.Color.green()
                )
                
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                embed.set_thumbnail(url=after.display_avatar.url)
                
                role_mentions = ", ".join([role.mention for role in added_roles])
                embed.add_field(name="Added Roles", value=role_mentions, inline=False)
                
                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.log_event(guild, embed, "member_update")
            
            if removed_roles:
                embed = discord.Embed(
                    title="Roles Removed",
                    description=f"{after.mention} lost {len(removed_roles)} role(s)",
                    color=discord.Color.red()
                )
                
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                embed.set_thumbnail(url=after.display_avatar.url)
                
                role_mentions = ", ".join([role.mention for role in removed_roles])
                embed.add_field(name="Removed Roles", value=role_mentions, inline=False)
                
                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.log_event(guild, embed, "member_update")
        
        # Check for timeouts
        if not before.is_timed_out() and after.is_timed_out():
            embed = discord.Embed(
                title="Member Timed Out",
                description=f"{after.mention} was timed out",
                color=discord.Color.orange()
            )
            
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=after.display_avatar.url)
            
            # Add timeout expiration
            expires_at = int(after.timed_out_until.timestamp())
            embed.add_field(
                name="Expires", 
                value=f"<t:{expires_at}:F> (<t:{expires_at}:R>)",
                inline=False
            )
            
            # Try to get the moderator who did this from audit logs
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and entry.created_at > (datetime.datetime.utcnow() - datetime.timedelta(seconds=5)):
                        moderator = entry.user
                        reason = entry.reason or "No reason provided"
                        
                        embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                        embed.add_field(name="Reason", value=reason, inline=True)
                        break
            except discord.Forbidden:
                pass
            
            embed.set_footer(text=f"User ID: {after.id}")
            
            await self.log_event(guild, embed, "member_update")
        
        # Check for timeout removals
        if before.is_timed_out() and not after.is_timed_out():
            embed = discord.Embed(
                title="Timeout Removed",
                description=f"{after.mention} is no longer timed out",
                color=discord.Color.green()
            )
            
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=after.display_avatar.url)
            
            # Try to get the moderator who did this from audit logs
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                    if entry.target.id == after.id and entry.created_at > (datetime.datetime.utcnow() - datetime.timedelta(seconds=5)):
                        moderator = entry.user
                        reason = entry.reason or "No reason provided"
                        
                        embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                        embed.add_field(name="Reason", value=reason, inline=True)
                        break
            except discord.Forbidden:
                pass
            
            embed.set_footer(text=f"User ID: {after.id}")
            
            await self.log_event(guild, embed, "member_update")
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log when a message is deleted"""
        # Ignore DMs and bot messages
        if not message.guild or message.author.bot:
            return
            
        guild = message.guild
        
        # Create embed
        embed = discord.Embed(
            title="Message Deleted",
            description=f"Message by {message.author.mention} deleted in {message.channel.mention}",
            color=discord.Color.red()
        )
        
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        
        # Add message content if available
        if message.content:
            # Truncate long messages
            content = message.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            
            embed.add_field(name="Content", value=content, inline=False)
        
        # Add attachments
        if message.attachments:
            attachment_list = "\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
            if len(attachment_list) > 1024:
                attachment_list = attachment_list[:1021] + "..."
                
            embed.add_field(name="Attachments", value=attachment_list, inline=False)
        
        # Add embeds count
        if message.embeds:
            embed.add_field(name="Embeds", value=str(len(message.embeds)), inline=True)
        
        # Add message ID and channel
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.set_footer(text=f"Message ID: {message.id} | Author ID: {message.author.id}")
        
        # Log the event
        await self.log_event(guild, embed, "message_delete")
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Log when messages are bulk deleted"""
        if not messages:
            return
            
        # Get first message's guild (they should all be from the same guild)
        message = messages[0]
        guild = message.guild
        channel = message.channel
        
        # Create embed
        embed = discord.Embed(
            title="Bulk Messages Deleted",
            description=f"{len(messages)} messages deleted in {channel.mention}",
            color=discord.Color.red()
        )
        
        # Try to get the moderator who did this from audit logs
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.message_bulk_delete):
                if entry.created_at > (datetime.datetime.utcnow() - datetime.timedelta(seconds=5)):
                    moderator = entry.user
                    reason = entry.reason or "No reason provided"
                    
                    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                    embed.add_field(name="Reason", value=reason, inline=True)
                    break
        except discord.Forbidden:
            pass
        
        # Add time
        embed.add_field(name="Time", value=f"<t:{int(datetime.datetime.utcnow().timestamp())}:F>", inline=True)
        
        # Add channel
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        
        # Add message count
        embed.add_field(name="Count", value=str(len(messages)), inline=True)
        
        # Log the event
        await self.log_event(guild, embed, "message_delete")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log when a message is edited"""
        # Ignore DMs, bot messages, and when content hasn't changed
        if (not before.guild or before.author.bot or 
            before.content == after.content):
            return
            
        guild = before.guild
        
        # Create embed
        embed = discord.Embed(
            title="Message Edited",
            description=f"Message by {before.author.mention} edited in {before.channel.mention}",
            color=discord.Color.blue()
        )
        
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        
        # Add before and after content
        if before.content:
            # Truncate long messages
            content = before.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            
            embed.add_field(name="Before", value=content, inline=False)
        
        if after.content:
            # Truncate long messages
            content = after.content
            if len(content) > 1024:
                content = content[:1021] + "..."
            
            embed.add_field(name="After", value=content, inline=False)
        
        # Add channel and jump URL
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Jump to Message", value=f"[Click Here]({after.jump_url})", inline=True)
        
        # Add message ID and author ID
        embed.set_footer(text=f"Message ID: {before.id} | Author ID: {before.author.id}")
        
        # Log the event
        await self.log_event(guild, embed, "message_edit")
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log when a channel is created"""
        guild = channel.guild
        
        # Create embed
        embed = discord.Embed(
            title="Channel Created",
            description=f"Channel {channel.mention} was created",
            color=discord.Color.green()
        )
        
        # Add channel info
        embed.add_field(name="Name", value=channel.name, inline=True)
        
        # Add channel type
        channel_type = "Unknown"
        if isinstance(channel, discord.TextChannel):
            channel_type = "Text Channel"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "Voice Channel"
        elif isinstance(channel, discord.CategoryChannel):
            channel_type = "Category"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "Stage Channel"
        elif hasattr(discord, 'ForumChannel') and isinstance(channel, discord.ForumChannel):
            channel_type = "Forum Channel"
            
        embed.add_field(name="Type", value=channel_type, inline=True)
        
        # Add category if in one
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        
        # Try to get the moderator who did this from audit logs
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id and entry.created_at > (datetime.datetime.utcnow() - datetime.timedelta(seconds=5)):
                    moderator = entry.user
                    reason = entry.reason or "No reason provided"
                    
                    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                    embed.add_field(name="Reason", value=reason, inline=True)
                    break
        except discord.Forbidden:
            pass
        
        # Add channel ID
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        # Log the event
        await self.log_event(guild, embed, "channel_create")
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log when a channel is deleted"""
        guild = channel.guild
        
        # Create embed
        embed = discord.Embed(
            title="Channel Deleted",
            description=f"Channel **{channel.name}** was deleted",
            color=discord.Color.red()
        )
        
        # Add channel info
        embed.add_field(name="Name", value=channel.name, inline=True)
        
        # Add channel type
        channel_type = "Unknown"
        if isinstance(channel, discord.TextChannel):
            channel_type = "Text Channel"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "Voice Channel"
        elif isinstance(channel, discord.CategoryChannel):
            channel_type = "Category"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "Stage Channel"
        elif hasattr(discord, 'ForumChannel') and isinstance(channel, discord.ForumChannel):
            channel_type = "Forum Channel"
            
        embed.add_field(name="Type", value=channel_type, inline=True)
        
        # Add category if in one
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        
        # Try to get the moderator who did this from audit logs
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id and entry.created_at > (datetime.datetime.utcnow() - datetime.timedelta(seconds=5)):
                    moderator = entry.user
                    reason = entry.reason or "No reason provided"
                    
                    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                    embed.add_field(name="Reason", value=reason, inline=True)
                    break
        except discord.Forbidden:
            pass
        
        # Add channel ID
        embed.set_footer(text=f"Channel ID: {channel.id}")
        
        # Log the event
        await self.log_event(guild, embed, "channel_delete")
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log when a role is created"""
        guild = role.guild
        
        # Create embed
        embed = discord.Embed(
            title="Role Created",
            description=f"Role {role.mention} was created",
            color=role.color or discord.Color.green()
        )
        
        # Add role info
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
        embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)
        
        # Try to get the moderator who did this from audit logs
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                if entry.target.id == role.id and entry.created_at > (datetime.datetime.utcnow() - datetime.timedelta(seconds=5)):
                    moderator = entry.user
                    reason = entry.reason or "No reason provided"
                    
                    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                    embed.add_field(name="Reason", value=reason, inline=True)
                    break
        except discord.Forbidden:
            pass
        
        # Add role ID
        embed.set_footer(text=f"Role ID: {role.id}")
        
        # Log the event
        await self.log_event(guild, embed, "role_create")
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log when a role is deleted"""
        guild = role.guild
        
        # Create embed
        embed = discord.Embed(
            title="Role Deleted",
            description=f"Role **{role.name}** was deleted",
            color=role.color or discord.Color.red()
        )
        
        # Add role info
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)
        
        # Try to get the moderator who did this from audit logs
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
                if entry.target.id == role.id and entry.created_at > (datetime.datetime.utcnow() - datetime.timedelta(seconds=5)):
                    moderator = entry.user
                    reason = entry.reason or "No reason provided"
                    
                    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                    embed.add_field(name="Reason", value=reason, inline=True)
                    break
        except discord.Forbidden:
            pass
        
        # Add role ID
        embed.set_footer(text=f"Role ID: {role.id}")
        
        # Log the event
        await self.log_event(guild, embed, "role_delete")
    
    @commands.group(name="logging", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def logging(self, ctx):
        """Server logging commands"""
        # Show current settings
        settings = self.get_guild_settings(ctx.guild.id)
        
        status = "Enabled" if settings.get("enabled", False) else "Disabled"
        channel_id = settings.get("log_channel")
        channel = ctx.guild.get_channel(int(channel_id)) if channel_id else None
        
        # Create embed
        embed = discord.Embed(
            title="Logging Settings",
            description=f"Current status: **{status}**",
            color=discord.Color.blue()
        )
        
        if channel:
            embed.add_field(name="Log Channel", value=channel.mention, inline=False)
        else:
            embed.add_field(name="Log Channel", value="Not set", inline=False)
        
        # Add event settings
        events_enabled = []
        events_disabled = []
        
        # Check event settings
        for key, value in settings.items():
            if key.startswith("log_") and key != "log_channel":
                event_name = key[4:]  # Remove "log_" prefix
                event_name = event_name.replace("_", " ").title()
                
                if value:
                    events_enabled.append(event_name)
                else:
                    events_disabled.append(event_name)
        
        if events_enabled:
            embed.add_field(name="Enabled Events", value=", ".join(events_enabled), inline=False)
        
        if events_disabled:
            embed.add_field(name="Disabled Events", value=", ".join(events_disabled), inline=False)
        
        # Add command help
        embed.add_field(
            name="Commands",
            value=(
                f"`{ctx.prefix}logging enable` - Enable logging\n"
                f"`{ctx.prefix}logging disable` - Disable logging\n"
                f"`{ctx.prefix}logging channel #channel` - Set log channel\n"
                f"`{ctx.prefix}logging events` - Toggle specific events"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @logging.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def logging_enable(self, ctx):
        """Enable logging for this server"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        # Check if already enabled
        if settings.get("enabled", False):
            await ctx.send("⚠️ Logging is already enabled.")
            return
        
        # Check if a log channel is set
        if not settings.get("log_channel"):
            await ctx.send("⚠️ You need to set a log channel first using `!logging channel #channel`")
            return
        
        # Enable logging
        settings["enabled"] = True
        self.update_guild_settings(ctx.guild.id, settings)
        
        # Confirm
        channel_id = settings.get("log_channel")
        channel = ctx.guild.get_channel(int(channel_id))
        
        embed = discord.Embed(
            title="✅ Logging Enabled",
            description=f"Server logs will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @logging.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def logging_disable(self, ctx):
        """Disable logging for this server"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        # Check if already disabled
        if not settings.get("enabled", False):
            await ctx.send("⚠️ Logging is already disabled.")
            return
        
        # Disable logging
        settings["enabled"] = False
        self.update_guild_settings(ctx.guild.id, settings)
        
        # Confirm
        embed = discord.Embed(
            title="✅ Logging Disabled",
            description="Server logs will no longer be recorded",
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
    
    @logging.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def logging_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for logging"""
        if not channel:
            # Show current channel
            settings = self.get_guild_settings(ctx.guild.id)
            channel_id = settings.get("log_channel")
            current_channel = ctx.guild.get_channel(int(channel_id)) if channel_id else None
            
            if current_channel:
                await ctx.send(f"Current logging channel: {current_channel.mention}")
            else:
                await ctx.send("No logging channel set. Use `!logging channel #channel` to set one.")
            return
        
        # Check if the bot has permission to send messages in the channel
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(f"⚠️ I don't have permission to send messages in {channel.mention}")
            return
        
        if not channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send(f"⚠️ I don't have permission to embed links in {channel.mention}")
            return
        
        # Update settings
        settings = self.get_guild_settings(ctx.guild.id)
        settings["log_channel"] = str(channel.id)
        self.update_guild_settings(ctx.guild.id, settings)
        
        # Confirm
        embed = discord.Embed(
            title="✅ Logging Channel Set",
            description=f"Server logs will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        
        # Send a test message to the channel
        test_embed = discord.Embed(
            title="Logging Channel Set",
            description=f"This channel has been set as the logging channel for this server by {ctx.author.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        
        await channel.send(embed=test_embed)
    
    @logging.command(name="events")
    @commands.has_permissions(manage_guild=True)
    async def logging_events(self, ctx):
        """Configure which events to log"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        # Create a list of events and their status
        events = []
        for key, value in settings.items():
            if key.startswith("log_") and key != "log_channel":
                event_name = key[4:]  # Remove "log_" prefix
                event_name = event_name.replace("_", " ").title()
                status = "✅ Enabled" if value else "❌ Disabled"
                
                events.append((key, event_name, value))
        
        # Create embed with event toggles
        embed = discord.Embed(
            title="Event Logging Settings",
            description="React to toggle events on/off",
            color=discord.Color.blue()
        )
        
        # Add events to the embed
        for i, (key, name, enabled) in enumerate(events, 1):
            status = "✅ Enabled" if enabled else "❌ Disabled"
            embed.add_field(
                name=f"{i}. {name}",
                value=status,
                inline=True
            )
        
        # Send the embed
        message = await ctx.send(embed=embed)
        
        # Add number reactions for toggle
        for i in range(1, len(events) + 1):
            await message.add_reaction(f"{i}\u20e3")  # Keycap digit
        
        # Add cancel reaction
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in [f"{i}\u20e3" for i in range(1, len(events) + 1)] + ["❌"] and reaction.message.id == message.id
        
        # Wait for reactions
        try:
            while True:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                
                # Remove the user's reaction
                try:
                    await message.remove_reaction(reaction, user)
                except:
                    pass
                
                # Cancel if X is clicked
                if str(reaction.emoji) == "❌":
                    await message.clear_reactions()
                    await message.edit(content="Event configuration cancelled.", embed=None)
                    return
                
                # Get the event index (1-based in display, 0-based in list)
                event_index = int(str(reaction.emoji)[0]) - 1
                
                # Toggle the event
                event_key, event_name, current_value = events[event_index]
                new_value = not current_value
                
                # Update the events list and settings
                events[event_index] = (event_key, event_name, new_value)
                settings[event_key] = new_value
                
                # Update the embed
                embed = discord.Embed(
                    title="Event Logging Settings",
                    description="React to toggle events on/off",
                    color=discord.Color.blue()
                )
                
                for i, (key, name, enabled) in enumerate(events, 1):
                    status = "✅ Enabled" if enabled else "❌ Disabled"
                    embed.add_field(
                        name=f"{i}. {name}",
                        value=status,
                        inline=True
                    )
                
                # Update the message
                await message.edit(embed=embed)
            
        except asyncio.TimeoutError:
            # Save settings on timeout
            self.update_guild_settings(ctx.guild.id, settings)
            
            # Update message
            await message.clear_reactions()
            await message.edit(content="✅ Event configuration saved!", embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize settings when joining a new guild"""
        # Check if we already have settings for this guild
        if str(guild.id) not in self.enabled_guilds:
            # Use default settings
            from config import DEFAULT_LOGGING_SETTINGS
            self.enabled_guilds[str(guild.id)] = DEFAULT_LOGGING_SETTINGS.copy()
            self.save_settings()
            
            # Try to find a suitable logging channel
            log_channel = discord.utils.get(guild.text_channels, name="bot-logs")
            if not log_channel:
                log_channel = discord.utils.get(guild.text_channels, name="logs")
            if not log_channel:
                log_channel = discord.utils.get(guild.text_channels, name="mod-logs")
            
            # If we found a channel, set it as the log channel
            if log_channel:
                self.enabled_guilds[str(guild.id)]["log_channel"] = str(log_channel.id)
                self.save_settings()
                
                # Send an introduction message
                try:
                    embed = discord.Embed(
                        title="Logging Module Initialized",
                        description=(
                            "This channel has been automatically set as the logging channel for this server.\n\n"
                            "Server administrators can change this using the `!logging channel` command.\n\n"
                            "Note: Logging is currently **disabled**. Use `!logging enable` to start logging events."
                        ),
                        color=discord.Color.blue(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    
                    await log_channel.send(embed=embed)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
