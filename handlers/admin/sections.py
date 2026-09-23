from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminRootCB, AdminSectionCB
from states.admin_states import AdminStates
from utils.msg import edit_or_send, show_card

SECTION_TITLES = {"values": "💎 Ценности", "standards": "📐 Стандарты"}
CLEAR_WORDS = {"-", "—", "удалить", "очистить", "нет"}

BULK_IMPORT_HELP = (
    "Массовый импорт пунктов.\n\n"
    "Пришлите текстом (или файлом .txt) список пунктов. Каждый пункт — "
    "первая строка это название, дальше до разделителя — описание "
    "(можно в несколько строк). Разделитель между пунктами — строка из "
    "трёх знаков равно: ===\n\n"
    "Например:\n\n"
    "Миссия\n"
    "Текст миссии, можно в несколько предложений.\n"
    "===\n"
    "Ключевая идея\n"
    "Текст ключевой идеи.\n"
    "===\n"
    "Эстетика\n"
    "Мы верим, что красота — это не роскошь, а ежедневная необходимость.\n\n"
    "Если сообщение слишком длинное для одного текста в Telegram — "
    "пришлите его как файл .txt (просто прикрепите файл, без сжатия)."
)


def _parse_bulk_items(text: str) -> list[tuple[str, str]]:
    """Разбирает текст на (название, описание) по разделителю "===" —
    строке, состоящей ровно из трёх знаков равно (пробелы вокруг не
    важны). Первая непустая строка блока — название, остальное —
    описание. Пустые блоки пропускаются."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[list[str]] = [[]]
    for line in lines:
        if line.strip() == "===":
            blocks.append([])
        else:
            blocks[-1].append(line)

    items = []
    for block in blocks:
        while block and not block[0].strip():
            block.pop(0)
        while block and not block[-1].strip():
            block.pop()
        if not block:
            continue
        title = block[0].strip()
        description = "\n".join(block[1:]).strip()
        if title:
            items.append((title, description))
    return items


def _list_title(section: str) -> str:
    return f"{SECTION_TITLES[section]} — управление\n\nВыберите пункт или добавьте новый:"


def _item_text(item) -> str:
    has_photo = "есть" if item["photo_file_id"] else "нет"
    desc = item["description"] or "(описание не заполнено)"
    return f"{item['title']}\n\n{desc}\n\n— — —\nФото: {has_photo}"


async def _send_item_card(message: Message, section: str, item_id: int) -> None:
    item = await db.get_section_item(item_id)
    text = _item_text(item)
    kb = admin_kb.section_item_kb(section, item_id)
    if item["photo_file_id"]:
        await message.answer_photo(photo=item["photo_file_id"], caption=text[:1024], reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@admin_router.callback_query(AdminRootCB.filter(F.action.in_({"values", "standards"})))
async def cb_open_section_admin(callback: CallbackQuery, callback_data: AdminRootCB, state: FSMContext) -> None:
    await state.clear()
    section = callback_data.action
    items = await db.get_section_items(section)
    await edit_or_send(callback, _list_title(section), admin_kb.section_list_kb(section, items))
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "list"))
async def cb_section_list(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await state.clear()
    section = callback_data.section
    items = await db.get_section_items(section)
    await edit_or_send(callback, _list_title(section), admin_kb.section_list_kb(section, items))
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "open"))
async def cb_section_open(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await state.clear()
    item = await db.get_section_item(callback_data.id)
    if item is None:
        await callback.answer("Пункт не найден.", show_alert=True)
        return
    text = _item_text(item)
    kb = admin_kb.section_item_kb(callback_data.section, item["id"])
    await show_card(callback, text, item["photo_file_id"], kb)
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "add"))
async def cb_section_add(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_section_title)
    await state.update_data(section=callback_data.section)
    await edit_or_send(callback, "Введите название нового пункта:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "rename"))
async def cb_section_rename(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_section_rename)
    await state.update_data(section=callback_data.section, item_id=callback_data.id)
    await edit_or_send(callback, "Введите новое название пункта:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "edit_desc"))
async def cb_section_edit_desc(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_section_description)
    await state.update_data(section=callback_data.section, item_id=callback_data.id)
    await edit_or_send(callback, "Введите текст описания пункта:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "edit_photo"))
async def cb_section_edit_photo(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_section_photo)
    await state.update_data(section=callback_data.section, item_id=callback_data.id)
    await edit_or_send(
        callback,
        "Пришлите фото для пункта.\nЧтобы убрать текущее фото — отправьте «-».",
        admin_kb.cancel_kb(),
    )
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "bulk_import"))
async def cb_section_bulk_import(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_section_bulk_import)
    await state.update_data(section=callback_data.section)
    await edit_or_send(callback, BULK_IMPORT_HELP, admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminSectionCB.filter(F.action == "delete"))
async def cb_section_delete(callback: CallbackQuery, callback_data: AdminSectionCB, state: FSMContext) -> None:
    await db.delete_section_item(callback_data.id)
    items = await db.get_section_items(callback_data.section)
    await edit_or_send(
        callback,
        f"Пункт удалён.\n\n{_list_title(callback_data.section)}",
        admin_kb.section_list_kb(callback_data.section, items),
    )
    await callback.answer("Пункт удалён")


@admin_router.message(AdminStates.waiting_section_title)
async def on_section_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    data = await state.get_data()
    section = data["section"]
    item_id = await db.add_section_item(section, title)
    await state.clear()
    await message.answer("Пункт создан ✅\nТеперь можно добавить описание и фото.")
    await _send_item_card(message, section, item_id)


@admin_router.message(AdminStates.waiting_section_rename)
async def on_section_rename(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    data = await state.get_data()
    await db.update_section_item(data["item_id"], title=title)
    await state.clear()
    await message.answer("Название обновлено ✅")
    await _send_item_card(message, data["section"], data["item_id"])


@admin_router.message(AdminStates.waiting_section_description)
async def on_section_description(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    data = await state.get_data()
    await db.update_section_item(data["item_id"], description=text)
    await state.clear()
    await message.answer("Описание обновлено ✅")
    await _send_item_card(message, data["section"], data["item_id"])


@admin_router.message(AdminStates.waiting_section_photo, F.photo)
async def on_section_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_id = message.photo[-1].file_id
    await db.update_section_item(data["item_id"], photo_file_id=file_id)
    await state.clear()
    await message.answer("Фото обновлено ✅")
    await _send_item_card(message, data["section"], data["item_id"])


@admin_router.message(AdminStates.waiting_section_photo, F.text)
async def on_section_photo_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    if text not in CLEAR_WORDS:
        await message.answer("Пришлите фото или «-», чтобы убрать текущее фото.", reply_markup=admin_kb.cancel_kb())
        return
    data = await state.get_data()
    await db.update_section_item(data["item_id"], photo_file_id=None)
    await state.clear()
    await message.answer("Фото удалено ✅")
    await _send_item_card(message, data["section"], data["item_id"])


@admin_router.message(AdminStates.waiting_section_photo)
async def on_section_photo_other(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Не получилось распознать сообщение. Пришлите фото или «-», чтобы убрать текущее фото.",
        reply_markup=admin_kb.cancel_kb(),
    )


async def _process_bulk_import(message: Message, state: FSMContext, text: str) -> None:
    items = _parse_bulk_items(text)
    if not items:
        await message.answer(
            "Не нашёл ни одного пункта. Проверьте формат (название — первая строка "
            "блока, разделитель между пунктами — отдельная строка \"===\") и "
            "пришлите ещё раз:",
            reply_markup=admin_kb.cancel_kb(),
        )
        return

    data = await state.get_data()
    section = data["section"]
    created_titles = []
    for title, description in items:
        await db.add_section_item(section, title, description)
        created_titles.append(title)
    await state.clear()

    summary = "\n".join(f"• {t}" for t in created_titles)
    await message.answer(f"Импортировано пунктов: {len(created_titles)} ✅\n\n{summary}")

    all_items = await db.get_section_items(section)
    await message.answer(_list_title(section), reply_markup=admin_kb.section_list_kb(section, all_items))


@admin_router.message(AdminStates.waiting_section_bulk_import, F.document)
async def on_section_bulk_import_document(message: Message, state: FSMContext) -> None:
    doc = message.document
    if doc.file_size and doc.file_size > 2_000_000:
        await message.answer(
            "Файл слишком большой. Пришлите файл поменьше или вставьте текст сообщением.",
            reply_markup=admin_kb.cancel_kb(),
        )
        return
    file = await message.bot.get_file(doc.file_id)
    buf = await message.bot.download_file(file.file_path)
    raw = buf.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1251", errors="replace")
    await _process_bulk_import(message, state, text)


@admin_router.message(AdminStates.waiting_section_bulk_import, F.text)
async def on_section_bulk_import_text(message: Message, state: FSMContext) -> None:
    await _process_bulk_import(message, state, message.text or "")


@admin_router.message(AdminStates.waiting_section_bulk_import)
async def on_section_bulk_import_other(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Пришлите текст со списком пунктов или файл .txt.", reply_markup=admin_kb.cancel_kb()
    )
