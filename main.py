import discord
import asyncio
import os
import sys
import logging
import threading
import time
from functools import lru_cache
from discord.ext import commands
from dotenv import load_dotenv  # Load environment variables
from config import DISCORD_TOKEN
from db_handler import init_db

# Import the Flask app for the web server workflow
try:
    from flask_app import app
except ImportError:
    app = None

# Setup Logging - Reduced to WARNING level with optimized format
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console handler
        # File handler is disabled to reduce disk I/O
    ]
)

# Optimize discord.py's own logging
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

# Enable only necessary Intents with fine-tuned options
intents = discord.Intents.default()
intents.message_content = True  # Required for text commands
intents.guilds = True  # Ensures the bot can see servers
intents.members = True  # Needed for user-related commands
# Disabled intents for better performance
intents.presences = False  # Significant payload reduction
intents.typing = False  # Reduces websocket traffic
intents.voice_states = False  # Disable unless needed by music module
# Re-enable only if your music module requires it
if any(f.startswith("music") for f in os.listdir("cogs") if f.endswith(".py")):
    intents.voice_states = True

# Custom performance optimized bot class
class OptimizedBot(commands.Bot):
    """Custom bot class with performance optimizations"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()
        self.command_counter = 0
        
        # Config cache with TTL (time-to-live)
        self._config_cache = {}
        self._config_timestamps = {}
        self._config_ttl = 300  # 5 minutes cache TTL
        
    @lru_cache(maxsize=128)
    def get_cached_prefix(self, guild_id):
        """Get guild prefix with LRU caching"""
        # Implementation will get prefix either from cache or DB
        # Default to the static prefix if not found
        return "lx "
        
    async def on_command(self, ctx):
        """Track command usage for analytics"""
        self.command_counter += 1
    
    def get_uptime(self):
        """Get bot uptime in seconds"""
        return time.time() - self.start_time

# Set Up Bot with optimized settings
bot = OptimizedBot(
    command_prefix="lx ", 
    intents=intents, 
    help_command=None,
    # Performance settings
    chunk_guilds_at_startup=False,  # Only load members when needed
    member_cache_flags=discord.MemberCacheFlags.none(),  # Minimal member caching
    max_messages=50,  # Smaller message cache 
    assume_unsync_clock=True,  # Better for distributed systems
)

# Event: When Bot is Ready
@bot.event
async def on_ready():
    # Don't initialize DB here (moved to main startup)
    logging.info(f"✅ Bot is online as {bot.user}")
    
    # Only sync commands if they've changed (tracked by file mod times)
    if should_sync_commands():
        try:
            # Reduced rate of syncing to avoid rate limits
            await bot.tree.sync()
            logging.info("✅ Slash commands synced successfully!")
        except Exception as e:
            logging.error(f"❌ Failed to sync slash commands: {e}")

# Track command file modifications
def should_sync_commands():
    """Determine if commands need to be synced based on file changes"""
    last_sync_file = ".last_sync"
    
    # Get latest cog modification time
    latest_mod_time = 0
    for file in os.listdir("cogs"):
        if file.endswith(".py"):
            file_path = os.path.join("cogs", file)
            mod_time = os.path.getmtime(file_path)
            latest_mod_time = max(latest_mod_time, mod_time)
    
    # Check if we need to sync
    try:
        if os.path.exists(last_sync_file):
            with open(last_sync_file, "r") as f:
                last_sync = float(f.read().strip())
            needs_sync = latest_mod_time > last_sync
        else:
            needs_sync = True
        
        # Update last sync time if needed
        if needs_sync:
            with open(last_sync_file, "w") as f:
                f.write(str(time.time()))
                
        return needs_sync
    except:
        # If any error, default to yes
        return True

# Load Cogs with Parallel Loading
async def load_extensions():
    """Load extensions with parallel optimization for faster startup"""
    # Initialize database early
    init_db()
    
    # Get all valid cog files
    cog_files = [
        f for f in os.listdir("cogs") 
        if f.endswith(".py") and f != "__init__.py"
    ]

    # Create a loader function for single extensions
    async def load_ext(file):
        cog_path = f"cogs.{file[:-3]}"
        try:
            await bot.load_extension(cog_path)
            # Use print instead of logging for immediate feedback
            print(f"✅ {cog_path} cog loaded!")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to load {cog_path}: {e}")
            return False
    
    # Group cogs by priority for staged loading
    priority_cogs = [f for f in cog_files if f.startswith(("help", "admin", "core"))]
    standard_cogs = [f for f in cog_files if f not in priority_cogs]
    
    # Load priority cogs first
    for file in priority_cogs:
        await load_ext(file)
    
    # Load remaining cogs in parallel for faster startup
    await asyncio.gather(*(load_ext(file) for file in standard_cogs))

# Restart Command
@bot.command(name="restart", help="🔄 Restarts the bot.")
@commands.is_owner()
async def restart(ctx):
    """Gracefully restarts the bot."""
    await ctx.send("🔄 Restarting bot...")
    logging.info("🔄 Restarting bot...")

    # Save any pending data before restart
    # Clear caches
    bot._config_cache.clear()
    
    # Restart more efficiently
    os.execv(sys.executable, ["python"] + sys.argv)

# Start the bot in a separate thread with error handling and retry
def run_discord_bot():
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            asyncio.run(bot_main())
            break  # If successful, exit the retry loop
        except (discord.ConnectionClosed, discord.GatewayNotFound) as e:
            if attempt < max_retries:
                wait_time = min(30, 2 ** attempt)  # Exponential backoff
                logging.warning(f"Connection error: {e}. Retrying in {wait_time}s (attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
            else:
                logging.error(f"Failed to connect after {max_retries} attempts: {e}")
                break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            break

async def bot_main():
    async with bot:
        # Load extensions and connect to Discord
        await load_extensions()
        await bot.start(DISCORD_TOKEN)

# Start Discord bot in a separate thread with improved thread management
def start_bot_thread():
    bot_thread = threading.Thread(target=run_discord_bot, name="DiscordBot")
    bot_thread.daemon = True
    bot_thread.start()

# We need to identify whether we're being run from the workflow or directly
# This ensures we don't run the bot twice
import sys
is_gunicorn = 'gunicorn' in sys.modules

# For Gunicorn/workflow (only start bot if running from the web workflow)
if __name__ != "__main__" and is_gunicorn:
    # Start the bot only if running through gunicorn
    start_bot_thread()

# For local development or when run directly
if __name__ == "__main__":
    try:
        # Start the minimal web server
        from keep_alive import keep_alive
        keep_alive()  # Start minimal web server on port 8080
        
        # Run the bot directly
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        logging.info("🛑 Bot shutdown initiated.")
    except Exception as e:
        logging.error(f"❌ Bot encountered an error: {e}")
