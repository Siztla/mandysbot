"""Идемпотентная загрузка учебного пособия «Стандарты сервиса Mandy's»
в раздел «Стандарты» одной кнопкой из админ-панели.

Пункты берутся из content/standards_seed.py (уже готовый HTML-текст,
дословно перенесённый из пособия). Существующие пункты с уже занятыми
названиями пропускаются — повторный запуск ничего не дублирует. Для
пунктов с картинкой файл загружается из assets/standards/ через
FSInputFile: только так можно получить настоящий Telegram file_id для
записи в БД (сам бот выполняет загрузку на своём сервере — из песочницы
Claude отправить файл в Telegram API нельзя)."""

from pathlib import Path

from aiogram import F
from aiogram.types import CallbackQuery, FSInputFile

from content.standards_seed import STANDARDS_SEED_ITEMS
from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminSectionCB
from utils.htmlsafe import esc

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "standards"


@admin_router.callback_query(
    AdminSectionCB.filter((F.section == "standards") & (F.action == "seed_standards"))
)
async def cb_seed_standards(callback: CallbackQuery) -> None:
    await callback.answer("Начинаю загрузку пособия, это займёт около минуты…")

    existing_items = await db.get_section_items("standards")
    existing_titles = {item["title"] for item in existing_items}

    created: list[str] = []
    skipped: list[str] = []

    for entry in STANDARDS_SEED_ITEMS:
        title = entry["title"]
        if title in existing_titles:
            skipped.append(title)
            continue

        photo_file_id = None
        image_name = entry.get("image")
        if image_name:
            image_path = ASSETS_DIR / image_name
            if image_path.exists():
                sent = await callback.message.answer_photo(FSInputFile(image_path))
                photo_file_id = sent.photo[-1].file_id
            else:
                await callback.message.answer(
                    f"⚠️ Не нашёл файл картинки {image_name} — пункт «{esc(title)}» "
                    f"будет создан без фото."
                )

        await db.add_section_item("standards", title, entry["html"], photo_file_id)
        created.append(title)

    lines = [f"Готово ✅\nСоздано новых пунктов: {len(created)}"]
    if created:
        lines.append("\n".join(f"• {esc(t)}" for t in created))
    if skipped:
        lines.append(f"Пропущено (уже существуют): {len(skipped)}")
    await callback.message.answer("\n\n".join(lines))

    items = await db.get_section_items("standards")
    await callback.message.answer(
        "📐 Стандарты — управление\n\nВыберите пункт или добавьте новый:",
        reply_markup=admin_kb.section_list_kb("standards", items),
    )
