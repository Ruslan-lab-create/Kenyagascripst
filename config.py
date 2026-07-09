import os
from dotenv import load_dotenv

load_dotenv()


def _get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
ADMIN_IDS = _get_admin_ids()
TRAFSLY_TOKEN = os.getenv("TRAFSLY_TOKEN", "")
TRAFSLY_BASE_URL = "https://api.trafsly.com"
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not ADMIN_IDS:
    raise RuntimeError("ADMIN_IDS не задан в .env — без этого никто не попадёт в админ-панель")
