import os

from dotenv import load_dotenv

load_dotenv()


def _clean(value: str) -> str:
    """Убирает то, что часто прилипает к значению при копировании в панель
    хостинга или в .env: пробелы, переносы строк, кавычки, невидимые
    символы."""
    value = (value or "").strip().strip("\"'").strip()
    return "".join(ch for ch in value if ch.isprintable() and not ch.isspace())


BOT_TOKEN = _clean(os.getenv("BOT_TOKEN", ""))

_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {
    int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()
}

DB_PATH = os.getenv("DB_PATH", "mandys.db").strip()

PROJECT_NAME = "Mandy's"


def masked_token(token: str = None) -> str:
    """Токен для логов: id бота и последние 4 символа секрета, остальное
    скрыто. По нему видно, какой именно токен подхватил бот, но сам токен
    в логи не попадает."""
    token = BOT_TOKEN if token is None else token
    if not token:
        return "<пусто>"
    bot_id, _, secret = token.partition(":")
    tail = secret[-4:] if len(secret) >= 4 else "?"
    return f"{bot_id}:…{tail} (длина {len(token)})"
