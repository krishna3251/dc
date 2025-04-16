import os
import discord
from typing import List, Set, Dict, Any

# Bot configuration
PREFIX = os.getenv("PREFIX", "deku")  # Default prefix is 'deku' if not set in env
TOKEN = os.getenv("DISCORD_TOKEN", "")  # Bot token from environment variable
DESCRIPTION = "Enhanced Discord bot with comprehensive moderation, logging, customization, and server management features"

# Owner IDs - people who have full access to the bot
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "").split(","))) if os.getenv("OWNER_IDS") else []

# Discord intents configuration
INTENTS = discord.Intents.default()  # Start with default intents
INTENTS.message_content = True  # Enable message content intent
INTENTS.members = True  # Enable members intent - needed for commands like userinfo and moderation
INTENTS.guilds = True  # Enable guild related data - needed for most commands
INTENTS.emojis_and_stickers = True  # Enable emoji and sticker related data

# Only enable additional privileged intents if configured in the Discord Developer Portal
try:
    # Check environment variable to see if full privileged intents are enabled
    if os.getenv("ENABLE_PRIVILEGED_INTENTS", "false").lower() == "true":
        INTENTS.presences = True  # Enable presence intent - shows user status
    else:
        print("Note: Full privileged intents not enabled. Some features like user status display will be limited.")
except Exception as e:
    print(f"Warning: Failed to set privileged intents: {e}")

# Status configuration
STATUS_TYPE = os.getenv("STATUS_TYPE", "watching")  # playing, watching, listening
STATUS_MESSAGE = os.getenv("STATUS_MESSAGE", "your server")

# List of cogs/extensions to load on startup
EXTENSIONS = [
    "anti_reply_cog",
    "anti_spam",
    "channel_perms",
    "gif_cog",
    "help_cog",
    "invite_cog",
    "mass_role_add_cog",
    "minfo",
    "ping",
    "purge_member_cog",
    "sarcastic_pinger",
    "search_cog",
    "vcperm",
    "spotify_cog",
    # New slash command extensions
    "slash_commands",
    "api_slash_commands"
]

# API Keys (set these in environment variables for security)
TENOR_API_KEY = os.getenv("TENOR_API_KEY", "")
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "")

# Default settings for various features
DEFAULT_AUTOMOD_SETTINGS = {
    "enabled": False,
    "filter_profanity": True,
    "filter_invites": True,
    "filter_links": False,
    "filter_mass_mentions": True,
    "filter_caps": True,
    "caps_threshold": 70,  # Percentage of capital letters
    "caps_min_length": 10,  # Minimum message length for caps filter
    "mention_threshold": 5,  # Max mentions in a message
    "warn_threshold": 3,  # Warnings before escalation
    "timeout_duration": 300,  # 5 minutes
    "log_channel": None
}

DEFAULT_LOGGING_SETTINGS = {
    "enabled": False,
    "log_channel": None,
    "log_member_join": True,
    "log_member_leave": True,
    "log_member_update": True,
    "log_message_edit": True,
    "log_message_delete": True,
    "log_channel_create": True,
    "log_channel_delete": True,
    "log_channel_update": True,
    "log_role_create": True,
    "log_role_delete": True,
    "log_role_update": True,
    "log_voice_state": True,
    "log_emoji_update": True,
    "log_server_update": True,
    "log_mod_actions": True
}

DEFAULT_WELCOME_SETTINGS = {
    "enabled": False,
    "channel": None,
    "message": "Welcome {user} to {server}! You are member #{count}.",
    "dm_enabled": False,
    "dm_message": "Welcome to {server}! Please read the rules and have a great time!",
    "image_enabled": False,
    "image_background": "default",
    "goodbye_enabled": False,
    "goodbye_channel": None,
    "goodbye_message": "Goodbye {user}! We hope to see you again soon."
}

DEFAULT_STATS_SETTINGS = {
    "enabled": False,
    "member_count_channel": None,
    "update_interval": 900,  # 15 minutes
    "display_bots": True,
    "display_online": True
}

DEFAULT_FILTER_SETTINGS = {
    "enabled": False,
    "filter_words": [],
    "filtered_channels": [],
    "exempt_roles": [],
    "action": "delete",  # delete, warn, timeout
    "notification": True,
    "dm_notification": False
}

DEFAULT_ACTIVITY_SETTINGS = {
    "enabled": False,
    "track_messages": True,
    "track_voice": True,
    "leaderboard_channel": None,
    "update_interval": 86400,  # 24 hours
    "top_count": 10,
    "point_settings": {
        "message": 1,
        "voice_minute": 2,
        "reaction": 0.5
    }
}

# Cooldown settings
COMMAND_COOLDOWNS = {
    "ping": 5,  # seconds
    "hug": 3,
    "slap": 3,
    "kiss": 3,
    "pat": 3,
    "poke": 3,
    "dance": 3,
    "cry": 3,
    "laugh": 3,
    "facepalm": 3,
    "highfive": 3,
    "gif": 5,
    "search": 10,
    "serverinfo": 30,
    "userinfo": 15
}

# Permission levels for custom commands
PERMISSION_LEVELS = {
    "everyone": 0,
    "manage_messages": 1,
    "manage_guild": 2,
    "administrator": 3,
    "owner": 4
}
