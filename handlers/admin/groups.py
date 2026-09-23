from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminGroupsCB, AdminRootCB
from states.admin_states import AdminStates
from utils.htmlsafe import esc
from utils.msg import edit_or_send

GROUPS_TITLE = "📋 Управление меню — группы\n\nВыберите группу или добавьте новую:"


def _group_card_text(group) -> str:
    return f"📂 Группа: {esc(group['title'])}\n\nID: {group['id']}"


@admin_router.callback_query(AdminGroupsCB.filter(F.action == "list"))
async def cb_groups_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    groups = await db.get_groups()
    await edit_or_send(callback, GROUPS_TITLE, admin_kb.groups_list_kb(groups))
    await callback.answer()


@admin_router.callback_query(AdminRootCB.filter(F.action == "menu"))
async def cb_admin_menu_open(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    groups = await db.get_groups()
    await edit_or_send(callback, GROUPS_TITLE, admin_kb.groups_list_kb(groups))
    await callback.answer()


@admin_router.callback_query(AdminGroupsCB.filter(F.action == "open"))
async def cb_group_open(callback: CallbackQuery, callback_data: AdminGroupsCB, state: FSMContext) -> None:
    await state.clear()
    group = await db.get_group(callback_data.id)
    if group is None:
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    await edit_or_send(callback, _group_card_text(group), admin_kb.group_card_kb(group["id"]))
    await callback.answer()


@admin_router.callback_query(AdminGroupsCB.filter(F.action == "add"))
async def cb_group_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_group_title)
    await edit_or_send(
        callback,
        "Введите название новой группы (например: «Завтраки»):",
        admin_kb.cancel_kb(),
    )
    await callback.answer()


@admin_router.callback_query(AdminGroupsCB.filter(F.action == "rename"))
async def cb_group_rename(callback: CallbackQuery, callback_data: AdminGroupsCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_group_rename)
    await state.update_data(group_id=callback_data.id)
    await edit_or_send(callback, "Введите новое название группы:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminGroupsCB.filter(F.action == "delete"))
async def cb_group_delete(callback: CallbackQuery, callback_data: AdminGroupsCB, state: FSMContext) -> None:
    await db.delete_group(callback_data.id)
    groups = await db.get_groups()
    await edit_or_send(callback, f"Группа удалена.\n\n{GROUPS_TITLE}", admin_kb.groups_list_kb(groups))
    await callback.answer("Группа и всё её содержимое удалены")


@admin_router.message(AdminStates.waiting_group_title)
async def on_group_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    group_id = await db.add_group(title)
    await state.clear()
    group = await db.get_group(group_id)
    await message.answer("Группа создана ✅")
    await message.answer(_group_card_text(group), reply_markup=admin_kb.group_card_kb(group_id))


@admin_router.message(AdminStates.waiting_group_rename)
async def on_group_rename(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    data = await state.get_data()
    group_id = data["group_id"]
    await db.update_group(group_id, title)
    await state.clear()
    group = await db.get_group(group_id)
    await message.answer("Название обновлено ✅")
    await message.answer(_group_card_text(group), reply_markup=admin_kb.group_card_kb(group_id))
