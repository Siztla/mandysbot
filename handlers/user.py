"""Пользовательская (обучающая) часть бота: онбординг, ценности,
стандарты, меню Mandy's."""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards import user_kb
from keyboards.callback_data import MainCB, SectionCB, MenuCB
from utils.formatting import format_position, format_section_item
from utils.msg import edit_or_send, show_card

router = Router(name="user")


# ---------------------------------------------------------------------------
# /start — онбординг + главное меню
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    onboarding = await db.get_onboarding()
    text = onboarding["text"]
    kb = user_kb.main_menu_kb()

    if onboarding["photo_file_id"]:
        caption = text if len(text) <= 1024 else text[:1021] + "…"
        await message.answer_photo(photo=onboarding["photo_file_id"], caption=caption, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(MainCB.filter(F.action == "root"))
async def cb_main_root(callback: CallbackQuery) -> None:
    onboarding = await db.get_onboarding()
    kb = user_kb.main_menu_kb()
    if onboarding["photo_file_id"]:
        await show_card(callback, onboarding["text"], onboarding["photo_file_id"], kb)
    else:
        await edit_or_send(callback, onboarding["text"], kb)
    await callback.answer()


# ---------------------------------------------------------------------------
# Ценности / Стандарты
# ---------------------------------------------------------------------------

SECTION_TITLES = {"values": "💎 Ценности Mandy's", "standards": "📐 Стандарты Mandy's"}


@router.callback_query(MainCB.filter(F.action.in_({"values", "standards"})))
async def cb_open_section(callback: CallbackQuery, callback_data: MainCB) -> None:
    section = callback_data.action
    items = await db.get_section_items(section)
    header = SECTION_TITLES[section]
    if not items:
        text = f"{header}\n\nРаздел пока пуст. Загляните позже."
    else:
        text = f"{header}\n\nВыберите пункт:"
    show_quiz = section == "standards" and await db.count_quiz_questions() > 0
    await edit_or_send(callback, text, user_kb.section_list_kb(section, items, show_quiz_button=show_quiz))
    await callback.answer()


@router.callback_query(SectionCB.filter(F.action == "list"))
async def cb_section_list(callback: CallbackQuery, callback_data: SectionCB) -> None:
    section = callback_data.section
    items = await db.get_section_items(section)
    header = SECTION_TITLES[section]
    text = f"{header}\n\nВыберите пункт:" if items else f"{header}\n\nРаздел пока пуст. Загляните позже."
    show_quiz = section == "standards" and await db.count_quiz_questions() > 0
    await edit_or_send(callback, text, user_kb.section_list_kb(section, items, show_quiz_button=show_quiz))
    await callback.answer()


@router.callback_query(SectionCB.filter(F.action == "view"))
async def cb_section_view(callback: CallbackQuery, callback_data: SectionCB) -> None:
    item = await db.get_section_item(callback_data.id)
    if item is None:
        await callback.answer("Пункт не найден, возможно он был удалён.", show_alert=True)
        return
    text = format_section_item(item)
    kb = user_kb.section_item_kb(callback_data.section)
    await show_card(callback, text, item["photo_file_id"], kb)
    await callback.answer()


# ---------------------------------------------------------------------------
# Меню: группы -> категории -> позиции
# ---------------------------------------------------------------------------

@router.callback_query(MainCB.filter(F.action == "menu"))
async def cb_open_menu(callback: CallbackQuery) -> None:
    groups = await db.get_groups()
    text = "📋 Меню Mandy's\n\nВыберите группу:"
    await edit_or_send(callback, text, user_kb.groups_list_kb(groups))
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "groups"))
async def cb_menu_groups(callback: CallbackQuery) -> None:
    groups = await db.get_groups()
    text = "📋 Меню Mandy's\n\nВыберите группу:"
    await edit_or_send(callback, text, user_kb.groups_list_kb(groups))
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "group"))
async def cb_menu_group(callback: CallbackQuery, callback_data: MenuCB) -> None:
    group = await db.get_group(callback_data.id)
    if group is None:
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    categories = await db.get_categories(group["id"])
    if not categories:
        text = f"📂 {group['title']}\n\nВ этой группе пока нет категорий."
        kb = user_kb.empty_list_kb(MenuCB(action="groups").pack())
    else:
        text = f"📂 {group['title']}\n\nВыберите категорию:"
        kb = user_kb.categories_list_kb(categories, group["id"])
    await edit_or_send(callback, text, kb)
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "category"))
async def cb_menu_category(callback: CallbackQuery, callback_data: MenuCB) -> None:
    category = await db.get_category(callback_data.id)
    if category is None:
        await callback.answer("Категория не найдена.", show_alert=True)
        return
    positions = await db.get_positions(category["id"])
    if not positions:
        text = f"🍽 {category['title']}\n\nВ этой категории пока нет позиций."
        kb = user_kb.empty_list_kb(MenuCB(action="group", id=category["group_id"]).pack())
    else:
        text = f"🍽 {category['title']}\n\nВыберите позицию:"
        kb = user_kb.positions_list_kb(positions, category["group_id"])
    await edit_or_send(callback, text, kb)
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "position"))
async def cb_menu_position(callback: CallbackQuery, callback_data: MenuCB) -> None:
    position = await db.get_position(callback_data.id)
    if position is None:
        await callback.answer("Позиция не найдена.", show_alert=True)
        return
    text = format_position(position)
    kb = user_kb.position_card_kb(position["category_id"])
    await show_card(callback, text, position["photo_file_id"], kb)
    await callback.answer()
