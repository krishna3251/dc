import discord
import asyncio
import os
import sys
import logging
from discord.ext import commands
from dotenv import load_dotenv  # Load environment variables
from config import DISCORD_TOKEN

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

# Proper Async Handling
async def main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_TOKEN)

# Start Bot with Proper Async Handling
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        logging.warning("⚠ Event loop already running. Switching to alternative method.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("🛑 Bot shutdown initiated.")
    except Exception as e:
        logging.error(f"❌ Bot encountered an error: {e}")
