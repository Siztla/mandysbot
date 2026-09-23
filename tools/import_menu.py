"""Массовый импорт меню в базу бота из data/menu/menu.json.

Импорт запускается тремя способами:

1. Автоматически при старте бота (bot.py): если файл меню изменился с
   прошлого импорта. Подходит для BotHost — ничего запускать руками не нужно.
2. Командой /import_menu в чате с ботом (только для администраторов).
3. Из консоли сервера, из корня проекта (там, где .env):

       python -m tools.import_menu --dry-run      # показать план, ничего не менять
       python -m tools.import_menu                # импорт с фото
       python -m tools.import_menu --no-photos    # только тексты

Что делает:
  • группы ищет по названию (создаёт, если группы нет);
  • в каждой группе использует первую категорию (создаёт категорию с
    названием группы, если категорий нет);
  • позицию ищет по названию внутри категории: есть — обновляет поля,
    нет — создаёт. Позиции, которых нет в файле, не трогает;
  • фото: бот отправляет каждое фото первому администратору, берёт file_id
    и сразу удаляет это сообщение. Уже загруженные фото повторно не
    отправляются. Если у позиции уже есть фото, оно не заменяется, пока не
    указан --replace-photos.

Повторный запуск не создаёт дублей. Перед импортом делается резервная копия
базы рядом с ней: <имя>.backup-<дата>.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from database import db  # noqa: E402

DATA_DIR = ROOT / "data" / "menu"
MENU_FILE = DATA_DIR / "menu.json"

log = logging.getLogger("menu_import")


def _norm(s: str) -> str:
    return " ".join(s.lower().replace("ё", "е").split())


def menu_file_hash() -> Optional[str]:
    if not MENU_FILE.exists():
        return None
    h = hashlib.sha256(MENU_FILE.read_bytes())
    for photo in sorted((DATA_DIR / "photos").glob("*")):
        h.update(photo.name.encode())
        h.update(str(photo.stat().st_size).encode())
    return h.hexdigest()[:20]


def _backup_db() -> Optional[Path]:
    src = Path(config.DB_PATH)
    if not src.exists():
        return None
    dst = src.with_name(f"{src.name}.backup-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(src, dst)
    return dst


class PhotoUploader:
    """Загружает локальные фото в Telegram через бота и возвращает file_id.
    file_id запоминаются в базе (таблица meta), чтобы не грузить повторно."""

    def __init__(self, bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id

    async def file_id(self, path: Path) -> str:
        from aiogram.exceptions import TelegramRetryAfter
        from aiogram.types import FSInputFile

        key = "photo:" + path.name + ":" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        cached = await db.get_meta(key)
        if cached:
            return cached
        while True:
            try:
                msg = await self.bot.send_photo(self.chat_id, FSInputFile(path), disable_notification=True)
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
        fid = msg.photo[-1].file_id
        try:
            await self.bot.delete_message(self.chat_id, msg.message_id)
        except Exception:
            pass
        await db.set_meta(key, fid)
        await asyncio.sleep(0.4)
        return fid


async def _find_group(title: str):
    for g in await db.get_groups():
        if _norm(g["title"]) == _norm(title):
            return g
    return None


async def _find_position(category_id: int, title: str):
    for p in await db.get_positions(category_id):
        if _norm(p["title"]) == _norm(title):
            return p
    return None


async def import_menu(
    uploader: Optional[PhotoUploader] = None,
    replace_photos: bool = False,
    dry_run: bool = False,
    say: Callable[[str], None] = print,
) -> dict:
    """Импортирует data/menu/menu.json. Возвращает статистику."""
    menu = json.loads(MENU_FILE.read_text("utf-8"))
    stats = dict(created=0, updated=0, photos=0, photo_errors=0, groups_created=0, categories_created=0)

    for g in menu["groups"]:
        group = await _find_group(g["title"])
        group_id = group["id"] if group else None
        if group is None:
            say(f"+ группа «{g['title']}»")
            stats["groups_created"] += 1
            if not dry_run:
                group_id = await db.add_group(g["title"])

        category_id = None
        if group_id is not None:
            cats = await db.get_categories(group_id)
            if cats:
                category_id = cats[0]["id"]
            else:
                say(f"  + категория «{g['title']}»")
                stats["categories_created"] += 1
                if not dry_run:
                    category_id = await db.add_category(group_id, g["title"])

        say(f"[{g['title']}] позиций: {len(g['positions'])}")
        for order, p in enumerate(g["positions"]):
            existing = await _find_position(category_id, p["title"]) if category_id else None
            photo_path = DATA_DIR / p["photo"] if p.get("photo") else None
            say(f"   {'обновить' if existing else 'создать'}: {p['title']}" + ("  📷" if photo_path else ""))
            if dry_run:
                stats["updated" if existing else "created"] += 1
                continue

            if existing:
                position_id = existing["id"]
                stats["updated"] += 1
            else:
                position_id = await db.add_position(category_id, p["title"])
                stats["created"] += 1

            fields = {
                "composition": p.get("composition", ""),
                "serving": p.get("serving", ""),
                "features": p.get("features", ""),
                "guest_description": p.get("guest", ""),
                "description": p.get("description", ""),
                "sort_order": order,
            }
            has_photo = bool(existing and existing["photo_file_id"])
            if uploader and photo_path and photo_path.exists() and (not has_photo or replace_photos):
                try:
                    fields["photo_file_id"] = await uploader.file_id(photo_path)
                    stats["photos"] += 1
                except Exception as e:  # фото не должно ломать импорт текста
                    stats["photo_errors"] += 1
                    say(f"   ⚠️ не удалось загрузить фото {photo_path.name}: {e}")
            await db.update_position(position_id, **fields)
    return stats


def format_stats(stats: dict, dry_run: bool = False) -> str:
    head = "План (ничего не изменено)" if dry_run else "Импорт меню завершён"
    text = (
        f"{head}: создано позиций {stats['created']}, обновлено {stats['updated']}, "
        f"загружено фото {stats['photos']}"
    )
    if stats.get("photo_errors"):
        text += f", ошибок загрузки фото {stats['photo_errors']}"
    if stats.get("groups_created") or stats.get("categories_created"):
        text += f", новых групп {stats['groups_created']}, новых категорий {stats['categories_created']}"
    return text + "."


async def pick_upload_chat() -> Optional[int]:
    ids = sorted(config.ADMIN_IDS) or sorted(await db.get_admin_ids())
    return ids[0] if ids else None


async def auto_import(bot) -> None:
    """Вызывается при старте бота: импортирует меню, если файл изменился."""
    current = menu_file_hash()
    if current is None:
        return
    if await db.get_meta("menu_import_hash") == current:
        return
    chat_id = await pick_upload_chat()
    uploader = PhotoUploader(bot, chat_id) if chat_id else None
    log.info("Меню изменилось — запускаю импорт (фото через чат %s)", chat_id)
    backup = _backup_db()
    if backup:
        log.info("Резервная копия базы: %s", backup)
    stats = await import_menu(uploader, say=lambda s: log.debug(s))
    log.info(format_stats(stats))
    if uploader and not stats["photo_errors"]:
        await db.set_meta("menu_import_hash", current)
    else:
        log.warning(
            "Фото загрузились не все — импорт повторится при следующем запуске. "
            "Проверьте, что администратор %s нажал /start в боте.", chat_id
        )


async def _cli(args) -> None:
    dry = args.dry_run
    if not dry:
        backup = _backup_db()
        print(f"Резервная копия базы: {backup}" if backup else "База ещё не создана — создаю новую.")
    elif not Path(config.DB_PATH).exists():
        sys.exit(f"База {config.DB_PATH} не найдена. Запустите бота хотя бы раз или импорт без --dry-run.")
    await db.init_db()

    bot = None
    uploader = None
    if not dry and not args.no_photos:
        if not config.BOT_TOKEN:
            sys.exit("BOT_TOKEN не задан в .env — без него фото не загрузить (или используйте --no-photos).")
        chat_id = args.chat_id or await pick_upload_chat()
        if not chat_id:
            sys.exit("Не найден ни один администратор. Укажите --chat-id <ваш Telegram ID>.")
        from aiogram import Bot

        bot = Bot(token=config.BOT_TOKEN)
        uploader = PhotoUploader(bot, chat_id)
        print(f"Фото загружаются через чат {chat_id} (сообщения сразу удаляются).")
    try:
        stats = await import_menu(uploader, replace_photos=args.replace_photos, dry_run=dry)
    finally:
        if bot:
            await bot.session.close()
    if not dry and not args.no_photos and not stats["photo_errors"]:
        await db.set_meta("menu_import_hash", menu_file_hash())
    print("\n" + format_stats(stats, dry))


def main() -> None:
    ap = argparse.ArgumentParser(description="Импорт меню Mandy's в базу бота")
    ap.add_argument("--dry-run", action="store_true", help="только показать, что будет сделано")
    ap.add_argument("--no-photos", action="store_true", help="не загружать фото")
    ap.add_argument("--replace-photos", action="store_true", help="заменить уже загруженные фото позиций")
    ap.add_argument("--chat-id", type=int, default=0, help="чат для загрузки фото (по умолчанию — первый админ)")
    asyncio.run(_cli(ap.parse_args()))


if __name__ == "__main__":
    main()
