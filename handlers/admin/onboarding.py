from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminRootCB, AdminOnboardingCB
from states.admin_states import AdminStates
from utils.msg import edit_or_send, show_card, send_card

CLEAR_WORDS = {"-", "—", "удалить", "очистить", "нет"}


def _onboarding_text(onboarding) -> str:
    has_photo = "есть" if onboarding["photo_file_id"] else "нет"
    return f"📝 Онбординг (первое сообщение сотрудника)\n\n{onboarding['text']}\n\n— — —\nФото: {has_photo}"


async def _send_onboarding_card(message: Message) -> None:
    onboarding = await db.get_onboarding()
    text = _onboarding_text(onboarding)
    kb = admin_kb.onboarding_kb()
    await send_card(message, text, onboarding["photo_file_id"], kb)


@admin_router.callback_query(AdminRootCB.filter(F.action == "onboarding"))
async def cb_onboarding_open(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    onboarding = await db.get_onboarding()
    text = _onboarding_text(onboarding)
    kb = admin_kb.onboarding_kb()
    await show_card(callback, text, onboarding["photo_file_id"], kb)
    await callback.answer()


@admin_router.callback_query(AdminOnboardingCB.filter(F.action == "edit_text"))
async def cb_onboarding_edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_onboarding_text)
    await edit_or_send(callback, "Введите новый текст онбординга:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminOnboardingCB.filter(F.action == "edit_photo"))
async def cb_onboarding_edit_photo(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_onboarding_photo)
    await edit_or_send(
        callback,
        "Пришлите фото для онбординга.\nЧтобы убрать текущее фото — отправьте «-».",
        admin_kb.cancel_kb(),
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_onboarding_text)
async def on_onboarding_text(message: Message, state: FSMContext) -> None:
    text = (message.html_text or message.text or "").strip()
    if not text:
        await message.answer("Текст не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    await db.update_onboarding(text=text)
    await state.clear()
    await message.answer("Текст онбординга обновлён ✅")
    await _send_onboarding_card(message)


@admin_router.message(AdminStates.waiting_onboarding_photo, F.photo)
async def on_onboarding_photo(message: Message, state: FSMContext) -> None:
    file_id = message.photo[-1].file_id
    await db.update_onboarding(photo_file_id=file_id)
    await state.clear()
    await message.answer("Фото онбординга обновлено ✅")
    await _send_onboarding_card(message)


@admin_router.message(AdminStates.waiting_onboarding_photo, F.text)
async def on_onboarding_photo_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    if text not in CLEAR_WORDS:
        await message.answer("Пришлите фото или «-», чтобы убрать текущее фото.", reply_markup=admin_kb.cancel_kb())
        return
    await db.update_onboarding(photo_file_id=None)
    await state.clear()
    await message.answer("Фото удалено ✅")
    await _send_onboarding_card(message)


@admin_router.message(AdminStates.waiting_onboarding_photo)
async def on_onboarding_photo_other(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Не получилось распознать сообщение. Пришлите фото или «-», чтобы убрать текущее фото.",
        reply_markup=admin_kb.cancel_kb(),
    )
