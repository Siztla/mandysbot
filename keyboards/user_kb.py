"""Клавиатуры для пользовательской (обучающей) части бота."""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callback_data import MainCB, SectionCB, MenuCB

BTN_VALUES = "💎 Ценности"
BTN_STANDARDS = "📐 Стандарты"
BTN_MENU = "📋 Меню"
BTN_HOME = "🏠 Главное меню"
BTN_ADMIN = "⚙️ Админ-панель"
BTN_BACK = "⬅️ Назад"


def reply_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=BTN_HOME)]]
    if is_admin:
        rows[0].append(KeyboardButton(text=BTN_ADMIN))
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=BTN_VALUES, callback_data=MainCB(action="values"))
    b.button(text=BTN_STANDARDS, callback_data=MainCB(action="standards"))
    b.button(text=BTN_MENU, callback_data=MainCB(action="menu"))
    b.adjust(1)
    return b.as_markup()


def section_list_kb(section: str, items) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item in items:
        b.button(text=item["title"], callback_data=SectionCB(section=section, action="view", id=item["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(text=BTN_BACK, callback_data=MainCB(action="root").pack()))
    return b.as_markup()


def section_item_kb(section: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=BTN_BACK, callback_data=SectionCB(section=section, action="list").pack()))
    return b.as_markup()


def groups_list_kb(groups) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for g in groups:
        b.button(text=g["title"], callback_data=MenuCB(action="group", id=g["id"]))
    b.adjust(2)
    b.row(InlineKeyboardButton(text=BTN_BACK, callback_data=MainCB(action="root").pack()))
    return b.as_markup()


def categories_list_kb(categories, group_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in categories:
        b.button(text=c["title"], callback_data=MenuCB(action="category", id=c["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(text=BTN_BACK, callback_data=MenuCB(action="groups").pack()))
    return b.as_markup()


def positions_list_kb(positions, group_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in positions:
        b.button(text=p["title"], callback_data=MenuCB(action="position", id=p["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(text=BTN_BACK, callback_data=MenuCB(action="group", id=group_id).pack()))
    return b.as_markup()


def position_card_kb(category_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=BTN_BACK, callback_data=MenuCB(action="category", id=category_id).pack()))
    return b.as_markup()


def empty_list_kb(back_cb: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=BTN_BACK, callback_data=back_cb))
    return b.as_markup()
