import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

SUBJECTS = {
    "English": 0x3498db,
    "Math": 0xe74c3c,
    "Science": 0x2ecc71,
    "GP": 0xf1c40f
}

DATABASE_PATH = os.getenv('DATABASE_PATH', 'tracker.db')

COMMAND_COOLDOWN = 1
MAX_MINUTES_PER_COMMAND = 720