import discord
import asyncio
import os
import sys
import logging
import threading
from discord.ext import commands
from dotenv import load_dotenv  # Load environment variables
from config import DISCORD_TOKEN
from db_handler import init_db

# Import the Flask app for the web server workflow
try:
    from flask_app import app
except ImportError:
    app = None

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")

# Enable Required Intents
intents = discord.Intents.default()
intents.message_content = True  # Required for text commands
intents.guilds = True  # Ensures the bot can see servers
intents.members = True  # Needed for user-related commands

# Set Up Bot
bot = commands.Bot(command_prefix="lx ", intents=intents, help_command=None)

# Event: When Bot is Ready
@bot.event
async def on_ready():
    logging.info(f"✅ Bot is online as {bot.user}")
    try:
        # Initialize the database
        init_db()
        # Sync slash commands
        await bot.tree.sync()  # Ensure slash commands are synced
        logging.info("✅ Slash commands synced successfully!")
    except Exception as e:
        logging.error(f"❌ Failed to sync slash commands: {e}")

# Load Cogs Dynamically
async def load_extensions():
    for file in os.listdir("cogs"):
        if file.endswith(".py") and file != "__init__.py":
            cog_path = f"cogs.{file[:-3]}"  # Format as 'cogs.help_cog'
            
            try:
                await bot.load_extension(cog_path)
                logging.info(f"✅ Loaded {cog_path}")
            except Exception as e:
                logging.error(f"❌ Failed to load {cog_path}: {e}")

# Restart Command
@bot.command(name="restart", help="🔄 Restarts the bot.")
@commands.is_owner()
async def restart(ctx):
    """Gracefully restarts the bot."""
    await ctx.send("🔄 Restarting bot...")
    logging.info("🔄 Restarting bot...")

    os.execv(sys.executable, ["python"] + sys.argv)  # Restart the bot process

# Start the bot in a separate thread
def run_discord_bot():
    asyncio.run(bot_main())

async def bot_main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_TOKEN)

# Start Discord bot in a separate thread
def start_bot_thread():
    bot_thread = threading.Thread(target=run_discord_bot)
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
