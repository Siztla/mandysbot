"""Клавиатуры для админ-панели."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.callback_data import (
    AdminRootCB,
    AdminGroupsCB,
    AdminCategoriesCB,
    AdminPositionsCB,
    AdminSectionCB,
    AdminOnboardingCB,
    AdminAdminsCB,
    AdminQuizCB,
    ADMIN_CANCEL,
)

BACK = "⬅️ Назад"


def cancel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data=ADMIN_CANCEL))
    return b.as_markup()


def admin_root_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📋 Управление меню", callback_data=AdminRootCB(action="menu"))
    b.button(text="💎 Ценности", callback_data=AdminRootCB(action="values"))
    b.button(text="📐 Стандарты", callback_data=AdminRootCB(action="standards"))
    b.button(text="📝 Онбординг", callback_data=AdminRootCB(action="onboarding"))
    b.button(text="🧪 Тест по стандартам", callback_data=AdminRootCB(action="quiz"))
    b.button(text="👤 Администраторы", callback_data=AdminRootCB(action="admins"))
    b.button(text="🚪 Выйти из админки", callback_data=AdminRootCB(action="exit"))
    b.adjust(1)
    return b.as_markup()


# --- Группы -------------------------------------------------------------

def groups_list_kb(groups) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for g in groups:
        b.button(text=g["title"], callback_data=AdminGroupsCB(action="open", id=g["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(text="➕ Добавить группу", callback_data=AdminGroupsCB(action="add").pack()))
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminRootCB(action="root").pack()))
    return b.as_markup()


def group_card_kb(group_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📂 Категории", callback_data=AdminCategoriesCB(action="list", group_id=group_id))
    b.button(text="✏️ Переименовать", callback_data=AdminGroupsCB(action="rename", id=group_id))
    b.button(text="🗑 Удалить группу", callback_data=AdminGroupsCB(action="delete", id=group_id))
    b.adjust(1)
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminGroupsCB(action="list").pack()))
    return b.as_markup()


# --- Категории ------------------------------------------------------------

def categories_list_kb(categories, group_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in categories:
        b.button(text=c["title"], callback_data=AdminCategoriesCB(action="open", group_id=group_id, id=c["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(
        text="➕ Добавить категорию",
        callback_data=AdminCategoriesCB(action="add", group_id=group_id).pack(),
    ))
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminGroupsCB(action="open", id=group_id).pack()))
    return b.as_markup()


def category_card_kb(group_id: int, category_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🍽 Позиции", callback_data=AdminPositionsCB(action="list", category_id=category_id))
    b.button(text="✏️ Переименовать", callback_data=AdminCategoriesCB(action="rename", group_id=group_id, id=category_id))
    b.button(text="🗑 Удалить категорию", callback_data=AdminCategoriesCB(action="delete", group_id=group_id, id=category_id))
    b.adjust(1)
    b.row(InlineKeyboardButton(
        text=BACK, callback_data=AdminCategoriesCB(action="list", group_id=group_id).pack()
    ))
    return b.as_markup()


# --- Позиции ----------------------------------------------------------------

def positions_list_kb(positions, category_id: int, group_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in positions:
        b.button(text=p["title"], callback_data=AdminPositionsCB(action="open", category_id=category_id, id=p["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(
        text="➕ Добавить позицию",
        callback_data=AdminPositionsCB(action="add", category_id=category_id).pack(),
    ))
    b.row(InlineKeyboardButton(
        text=BACK, callback_data=AdminCategoriesCB(action="open", group_id=group_id, id=category_id).pack()
    ))
    return b.as_markup()


def position_card_kb(category_id: int, position_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Название", callback_data=AdminPositionsCB(action="edit_title", category_id=category_id, id=position_id))
    b.button(text="🖼 Фото", callback_data=AdminPositionsCB(action="edit_photo", category_id=category_id, id=position_id))
    b.button(text="📝 Состав", callback_data=AdminPositionsCB(action="edit_composition", category_id=category_id, id=position_id))
    b.button(text="🍴 Подача", callback_data=AdminPositionsCB(action="edit_serving", category_id=category_id, id=position_id))
    b.button(text="✨ Особенности", callback_data=AdminPositionsCB(action="edit_features", category_id=category_id, id=position_id))
    b.button(text="💬 Для гостя", callback_data=AdminPositionsCB(action="edit_guest", category_id=category_id, id=position_id))
    b.button(text="📋 Описание", callback_data=AdminPositionsCB(action="edit_description", category_id=category_id, id=position_id))
    b.button(text="⚠️ Аллергены", callback_data=AdminPositionsCB(action="edit_allergens", category_id=category_id, id=position_id))
    b.button(text="🥂 С чем подаётся", callback_data=AdminPositionsCB(action="edit_served", category_id=category_id, id=position_id))
    b.button(text="👁 Предпросмотр", callback_data=AdminPositionsCB(action="preview", category_id=category_id, id=position_id))
    b.button(text="🗑 Удалить позицию", callback_data=AdminPositionsCB(action="delete", category_id=category_id, id=position_id))
    b.adjust(2, 2, 2, 2, 2, 1, 1)
    b.row(InlineKeyboardButton(
        text=BACK, callback_data=AdminPositionsCB(action="list", category_id=category_id).pack()
    ))
    return b.as_markup()


def back_to_position_kb(category_id: int, position_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text=BACK, callback_data=AdminPositionsCB(action="open", category_id=category_id, id=position_id).pack()
    ))
    return b.as_markup()


# --- Ценности / Стандарты ----------------------------------------------------

def section_list_kb(section: str, items) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for it in items:
        b.button(text=it["title"], callback_data=AdminSectionCB(section=section, action="open", id=it["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(
        text="➕ Добавить пункт", callback_data=AdminSectionCB(section=section, action="add").pack()
    ))
    b.row(InlineKeyboardButton(
        text="📥 Массовый импорт", callback_data=AdminSectionCB(section=section, action="bulk_import").pack()
    ))
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminRootCB(action="root").pack()))
    return b.as_markup()


def section_item_kb(section: str, item_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Название", callback_data=AdminSectionCB(section=section, action="rename", id=item_id))
    b.button(text="📝 Описание", callback_data=AdminSectionCB(section=section, action="edit_desc", id=item_id))
    b.button(text="🖼 Фото", callback_data=AdminSectionCB(section=section, action="edit_photo", id=item_id))
    b.button(text="🗑 Удалить", callback_data=AdminSectionCB(section=section, action="delete", id=item_id))
    b.adjust(2, 2)
    b.row(InlineKeyboardButton(
        text=BACK, callback_data=AdminSectionCB(section=section, action="list").pack()
    ))
    return b.as_markup()


# --- Онбординг ----------------------------------------------------------------

def onboarding_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Текст", callback_data=AdminOnboardingCB(action="edit_text"))
    b.button(text="🖼 Фото", callback_data=AdminOnboardingCB(action="edit_photo"))
    b.adjust(1)
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminRootCB(action="root").pack()))
    return b.as_markup()


# --- Администраторы -----------------------------------------------------------

def admins_list_kb(admin_ids) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for uid in admin_ids:
        b.button(text=f"➖ {uid}", callback_data=AdminAdminsCB(action="remove", id=uid))
    b.adjust(1)
    b.row(InlineKeyboardButton(text="➕ Добавить администратора", callback_data=AdminAdminsCB(action="add").pack()))
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminRootCB(action="root").pack()))
    return b.as_markup()


# --- Тест по стандартам --------------------------------------------------

def quiz_list_kb(questions) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for q in questions:
        label = q["question"] if len(q["question"]) <= 60 else q["question"][:57] + "…"
        b.button(text=label, callback_data=AdminQuizCB(action="open", id=q["id"]))
    b.adjust(1)
    b.row(InlineKeyboardButton(text="➕ Добавить вопрос", callback_data=AdminQuizCB(action="add").pack()))
    b.row(InlineKeyboardButton(text="📊 Результаты сотрудников", callback_data=AdminQuizCB(action="results").pack()))
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminRootCB(action="root").pack()))
    return b.as_markup()


def quiz_question_card_kb(question_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Текст вопроса", callback_data=AdminQuizCB(action="edit_text", id=question_id))
    b.button(text="🔄 Варианты ответов", callback_data=AdminQuizCB(action="edit_options", id=question_id))
    b.button(text="🗑 Удалить вопрос", callback_data=AdminQuizCB(action="delete", id=question_id))
    b.adjust(2, 1)
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminQuizCB(action="list").pack()))
    return b.as_markup()


def quiz_list_or_back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=BACK, callback_data=AdminQuizCB(action="list").pack()))
    return b.as_markup()
