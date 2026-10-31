import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Discord Bot Credentials
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()

# Whitelisted User IDs (comma separated integers)
_raw_allowed = os.getenv("ALLOWED_USER_IDS", "").strip()
if _raw_allowed:
    ALLOWED_USER_IDS = [int(x.strip()) for x in _raw_allowed.split(",") if x.strip().isdigit()]
else:
    ALLOWED_USER_IDS = []

# Command prefix for text commands (slash commands also supported)
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")

# Default paths
DEFAULT_WORKSPACE = os.getenv("DEFAULT_WORKSPACE", str(Path.home()))
AGY_PATH = os.getenv("AGY_PATH", "agy")

# Email settings (optional for touchless reports)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
DEFAULT_EMAIL_TO = os.getenv("DEFAULT_EMAIL_TO", "")

# Static persistent remote touch token (optional, persistent bookmark)
REMOTE_STATIC_TOKEN = os.getenv("REMOTE_STATIC_TOKEN", "").strip()

def is_authorized(user_id: int) -> bool:
    """Security guard: only allow registered owner/user IDs."""
    if not ALLOWED_USER_IDS:
        return False
    return user_id in ALLOWED_USER_IDS
