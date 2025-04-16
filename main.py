import discord
import asyncio
import os
import sys
import logging
import threading
import time
from functools import lru_cache
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from config import TOKEN, PREFIX, INTENTS, EXTENSIONS
from database import init_app

try:
    from flask import Flask
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bot.db"
    init_app(app)
except ImportError:
    app = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[logging.StreamHandler()]
)

class OptimizedBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()
        self.command_counter = 0
        self._config_cache = {}
        self._config_timestamps = {}
        self._config_ttl = 300

    @lru_cache(maxsize=128)
    def get_cached_prefix(self, guild_id):
        return PREFIX

    async def on_command(self, ctx):
        self.command_counter += 1

    def get_uptime(self):
        return time.time() - self.start_time

bot = OptimizedBot(
    command_prefix=PREFIX,
    intents=INTENTS,
    help_command=None
)

@bot.event
async def on_ready():
    logging.info(f"\u2705 Bot is online as {bot.user}")
    if should_sync_commands():
        try:
            await bot.tree.sync()
            logging.info("\u2705 Slash commands synced!")
        except Exception as e:
            logging.error(f"❌ Slash command sync failed: {e}")

def should_sync_commands():
    last_sync_file = ".last_sync"
    latest_mod_time = 0
    for file in os.listdir("cogs"):
        if file.endswith(".py"):
            mod_time = os.path.getmtime(os.path.join("cogs", file))
            latest_mod_time = max(latest_mod_time, mod_time)

    try:
        if os.path.exists(last_sync_file):
            with open(last_sync_file, "r") as f:
                last_sync = float(f.read().strip())
            needs_sync = latest_mod_time > last_sync
        else:
            needs_sync = True

        if needs_sync:
            with open(last_sync_file, "w") as f:
                f.write(str(time.time()))

        return needs_sync
    except:
        return True

async def load_extensions():
    from database import db
    cog_files = [f for f in os.listdir("cogs") if f.endswith(".py") and f != "__init__.py"]

    async def load_ext(file):
        cog_path = f"cogs.{file[:-3]}"
        try:
            await bot.load_extension(cog_path)
            logging.info(f"\u2705 Loaded cog: {cog_path}")
        except Exception as e:
            logging.error(f"❌ Failed to load {cog_path}: {e}", exc_info=True)

    priority = [f for f in cog_files if f.startswith(("help", "admin", "core", "spotify"))]
    rest = [f for f in cog_files if f not in priority]

    for file in priority:
        await load_ext(file)

    await asyncio.gather(*(load_ext(file) for file in rest))

    logging.info(f"\u2705 Loaded {len(priority) + len(rest)} extensions.")

@bot.command(name="restart")
@commands.is_owner()
async def restart(ctx):
    await ctx.send("\ud83d\udd04 Restarting...")
    logging.info("Restarting bot...")
    bot._config_cache.clear()
    os.execv(sys.executable, ["python"] + sys.argv)

@bot.command(name="reload")
@commands.is_owner()
async def reload_cog(ctx, cog: str):
    try:
        await bot.reload_extension(f"cogs.{cog}")
        await ctx.send(f"\ud83d\udd01 Reloaded `{cog}` successfully.")
    except Exception as e:
        await ctx.send(f"\u274c Error reloading `{cog}`:\n```{e}```")

@bot.command(name="uptime")
async def uptime(ctx):
    uptime = bot.get_uptime()
    await ctx.send(f"\u23f1\ufe0f Bot uptime: `{int(uptime // 60)} minutes`.")

def run_discord_bot():
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            asyncio.run(bot_main())
            break
        except (discord.ConnectionClosed, discord.GatewayNotFound) as e:
            wait_time = min(30, 2 ** attempt)
            logging.warning(f"Connection error: {e}. Retrying in {wait_time}s")
            time.sleep(wait_time)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            break

async def bot_main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

def start_bot_thread():
    bot_thread = threading.Thread(target=run_discord_bot, name="DiscordBot")
    bot_thread.daemon = True
    bot_thread.start()

is_gunicorn = 'gunicorn' in sys.modules

if __name__ != "__main__" and is_gunicorn:
    start_bot_thread()

if __name__ == "__main__":
    try:
        from keep_alive import keep_alive
        keep_alive()
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        logging.info("\ud83d\uded1 Bot shutdown.")
    except Exception as e:
        logging.error(f"\u274c Critical Error: {e}")
