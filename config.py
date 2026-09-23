import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {
    int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()
}

DB_PATH = os.getenv("DB_PATH", "mandys.db")

PROJECT_NAME = "Mandy's"
