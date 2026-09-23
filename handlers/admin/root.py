from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb, user_kb
from keyboards.callback_data import AdminRootCB, ADMIN_CANCEL
from utils.access import is_admin
from utils.msg import edit_or_send

ADMIN_TITLE = "⚙️ Админ-панель Mandy's\n\nВыберите раздел:"


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return
    await state.clear()
    await message.answer(ADMIN_TITLE, reply_markup=admin_kb.admin_root_kb())


@admin_router.callback_query(AdminRootCB.filter(F.action == "root"))
async def cb_admin_root(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_or_send(callback, ADMIN_TITLE, admin_kb.admin_root_kb())
    await callback.answer()


@admin_router.callback_query(AdminRootCB.filter(F.action == "exit"))
async def cb_admin_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    onboarding = await db.get_onboarding()
    await edit_or_send(callback, onboarding["text"], user_kb.main_menu_kb())
    await callback.answer("Вы вышли из админ-панели")


@admin_router.callback_query(F.data == ADMIN_CANCEL)
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await edit_or_send(callback, ADMIN_TITLE, admin_kb.admin_root_kb())
    await callback.answer("Отменено")
