from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminRootCB, AdminAdminsCB
from states.admin_states import AdminStates
from utils.msg import edit_or_send

LIST_TITLE = (
    "👤 Администраторы бота\n\n"
    "Ниже — Telegram ID действующих администраторов. Чтобы узнать свой ID, "
    "можно написать боту @userinfobot.\n\n"
    "Нажмите ➖ рядом с ID, чтобы отозвать доступ."
)


async def _render_list():
    admin_ids = sorted(await db.get_admin_ids())
    return LIST_TITLE, admin_kb.admins_list_kb(admin_ids)


@admin_router.callback_query(AdminRootCB.filter(F.action == "admins"))
async def cb_admins_open(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text, kb = await _render_list()
    await edit_or_send(callback, text, kb)
    await callback.answer()


@admin_router.callback_query(AdminAdminsCB.filter(F.action == "list"))
async def cb_admins_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text, kb = await _render_list()
    await edit_or_send(callback, text, kb)
    await callback.answer()


@admin_router.callback_query(AdminAdminsCB.filter(F.action == "add"))
async def cb_admins_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_admin_id_add)
    await edit_or_send(
        callback,
        "Пришлите Telegram ID пользователя, которого нужно сделать администратором "
        "(числовой ID, его можно узнать через @userinfobot):",
        admin_kb.cancel_kb(),
    )
    await callback.answer()


@admin_router.callback_query(AdminAdminsCB.filter(F.action == "remove"))
async def cb_admins_remove(callback: CallbackQuery, callback_data: AdminAdminsCB, state: FSMContext) -> None:
    admin_ids = await db.get_admin_ids()
    if len(admin_ids) <= 1:
        await callback.answer("Нельзя удалить последнего администратора.", show_alert=True)
        return
    await db.remove_admin(callback_data.id)
    text, kb = await _render_list()
    await edit_or_send(callback, text, kb)
    await callback.answer("Администратор удалён")


@admin_router.message(AdminStates.waiting_admin_id_add)
async def on_admin_id_add(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.lstrip("-").isdigit():
        await message.answer(
            "Нужно прислать числовой Telegram ID. Попробуйте ещё раз:",
            reply_markup=admin_kb.cancel_kb(),
        )
        return
    user_id = int(raw)
    await db.add_admin(user_id)
    await state.clear()
    await message.answer(f"Пользователь {user_id} добавлен в администраторы ✅")
    admin_ids = sorted(await db.get_admin_ids())
    await message.answer(LIST_TITLE, reply_markup=admin_kb.admins_list_kb(admin_ids))
