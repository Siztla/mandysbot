from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminCategoriesCB
from states.admin_states import AdminStates
from utils.msg import edit_or_send


def _categories_title(group) -> str:
    return f"📂 {group['title']} — категории\n\nВыберите категорию или добавьте новую:"


def _category_card_text(group, category) -> str:
    return f"🗂 Категория: {category['title']}\nГруппа: {group['title']}\n\nID: {category['id']}"


@admin_router.callback_query(AdminCategoriesCB.filter(F.action == "list"))
async def cb_categories_list(callback: CallbackQuery, callback_data: AdminCategoriesCB, state: FSMContext) -> None:
    await state.clear()
    group = await db.get_group(callback_data.group_id)
    if group is None:
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    categories = await db.get_categories(group["id"])
    await edit_or_send(callback, _categories_title(group), admin_kb.categories_list_kb(categories, group["id"]))
    await callback.answer()


@admin_router.callback_query(AdminCategoriesCB.filter(F.action == "open"))
async def cb_category_open(callback: CallbackQuery, callback_data: AdminCategoriesCB, state: FSMContext) -> None:
    await state.clear()
    category = await db.get_category(callback_data.id)
    if category is None:
        await callback.answer("Категория не найдена.", show_alert=True)
        return
    group = await db.get_group(category["group_id"])
    await edit_or_send(
        callback,
        _category_card_text(group, category),
        admin_kb.category_card_kb(group["id"], category["id"]),
    )
    await callback.answer()


@admin_router.callback_query(AdminCategoriesCB.filter(F.action == "add"))
async def cb_category_add(callback: CallbackQuery, callback_data: AdminCategoriesCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_category_title)
    await state.update_data(group_id=callback_data.group_id)
    await edit_or_send(
        callback,
        "Введите название новой категории (например: «Горячие блюда»):",
        admin_kb.cancel_kb(),
    )
    await callback.answer()


@admin_router.callback_query(AdminCategoriesCB.filter(F.action == "rename"))
async def cb_category_rename(callback: CallbackQuery, callback_data: AdminCategoriesCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_category_rename)
    await state.update_data(category_id=callback_data.id, group_id=callback_data.group_id)
    await edit_or_send(callback, "Введите новое название категории:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminCategoriesCB.filter(F.action == "delete"))
async def cb_category_delete(callback: CallbackQuery, callback_data: AdminCategoriesCB, state: FSMContext) -> None:
    await db.delete_category(callback_data.id)
    group = await db.get_group(callback_data.group_id)
    categories = await db.get_categories(callback_data.group_id)
    await edit_or_send(
        callback,
        f"Категория удалена.\n\n{_categories_title(group)}",
        admin_kb.categories_list_kb(categories, callback_data.group_id),
    )
    await callback.answer("Категория и все её позиции удалены")


@admin_router.message(AdminStates.waiting_category_title)
async def on_category_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    data = await state.get_data()
    group_id = data["group_id"]
    category_id = await db.add_category(group_id, title)
    await state.clear()
    group = await db.get_group(group_id)
    category = await db.get_category(category_id)
    await message.answer("Категория создана ✅")
    await message.answer(
        _category_card_text(group, category),
        reply_markup=admin_kb.category_card_kb(group_id, category_id),
    )


@admin_router.message(AdminStates.waiting_category_rename)
async def on_category_rename(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    data = await state.get_data()
    category_id = data["category_id"]
    group_id = data["group_id"]
    await db.update_category(category_id, title)
    await state.clear()
    group = await db.get_group(group_id)
    category = await db.get_category(category_id)
    await message.answer("Название обновлено ✅")
    await message.answer(
        _category_card_text(group, category),
        reply_markup=admin_kb.category_card_kb(group_id, category_id),
    )
