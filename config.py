import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GOOGLE_API_KEY = os.getenv("AIzaSyBEB9dwPGt6b0OHBK5BTlx88nSEqKffTT0")
GOOGLE_CSE_ID = os.getenv("b22a1caf922df4ee3")
# Get the bot token from .env
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    raise ValueError("❌ DISCORD_TOKEN is missing! Check your .env file.")
