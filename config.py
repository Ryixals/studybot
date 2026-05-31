import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

SUBJECTS = {
    "English": 0x1EA0FF,
    "Math": 0xFF1E32,
    "Science": 0x1EC81E,
    "GP": 0xF5D20A
}

DATABASE_PATH = os.getenv('DATABASE_PATH', 'tracker.db')

COMMAND_COOLDOWN = 1
MAX_MINUTES_PER_COMMAND = 720