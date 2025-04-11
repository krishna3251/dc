import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the bot token from .env
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    raise ValueError("❌ DISCORD_TOKEN is missing! Check your .env file.")
