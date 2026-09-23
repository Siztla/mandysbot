from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminPositionsCB
from states.admin_states import AdminStates
from utils.formatting import format_position, format_position_admin
from utils.htmlsafe import esc
from utils.msg import edit_or_send, show_card, send_card

CLEAR_WORDS = {"-", "—", "удалить", "очистить", "нет"}


def _positions_title(category) -> str:
    return f"🍽 {esc(category['title'])} — позиции\n\nВыберите позицию или добавьте новую:"


async def _show_position_card(callback: CallbackQuery, position_id: int) -> None:
    position = await db.get_position(position_id)
    text = format_position_admin(position)
    kb = admin_kb.position_card_kb(position["category_id"], position["id"])
    await show_card(callback, text, position["photo_file_id"], kb)


async def _send_position_card(message: Message, position_id: int) -> None:
    position = await db.get_position(position_id)
    text = format_position_admin(position)
    kb = admin_kb.position_card_kb(position["category_id"], position["id"])
    await send_card(message, text, position["photo_file_id"], kb)


@admin_router.callback_query(AdminPositionsCB.filter(F.action == "list"))
async def cb_positions_list(callback: CallbackQuery, callback_data: AdminPositionsCB, state: FSMContext) -> None:
    await state.clear()
    category = await db.get_category(callback_data.category_id)
    if category is None:
        await callback.answer("Категория не найдена.", show_alert=True)
        return
    positions = await db.get_positions(category["id"])
    await edit_or_send(
        callback,
        _positions_title(category),
        admin_kb.positions_list_kb(positions, category["id"], category["group_id"]),
    )
    await callback.answer()


@admin_router.callback_query(AdminPositionsCB.filter(F.action == "open"))
async def cb_position_open(callback: CallbackQuery, callback_data: AdminPositionsCB, state: FSMContext) -> None:
    await state.clear()
    position = await db.get_position(callback_data.id)
    if position is None:
        await callback.answer("Позиция не найдена.", show_alert=True)
        return
    await _show_position_card(callback, position["id"])
    await callback.answer()


@admin_router.callback_query(AdminPositionsCB.filter(F.action == "preview"))
async def cb_position_preview(callback: CallbackQuery, callback_data: AdminPositionsCB, state: FSMContext) -> None:
    position = await db.get_position(callback_data.id)
    if position is None:
        await callback.answer("Позиция не найдена.", show_alert=True)
        return
    text = "👁 Так видит сотрудник:\n\n" + format_position(position)
    kb = admin_kb.back_to_position_kb(position["category_id"], position["id"])
    await show_card(callback, text, position["photo_file_id"], kb)
    await callback.answer()


@admin_router.callback_query(AdminPositionsCB.filter(F.action == "add"))
async def cb_position_add(callback: CallbackQuery, callback_data: AdminPositionsCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_position_title)
    await state.update_data(category_id=callback_data.category_id)
    await edit_or_send(callback, "Введите название новой позиции (блюда/напитка):", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminPositionsCB.filter(F.action == "delete"))
async def cb_position_delete(callback: CallbackQuery, callback_data: AdminPositionsCB, state: FSMContext) -> None:
    await db.delete_position(callback_data.id)
    category = await db.get_category(callback_data.category_id)
    positions = await db.get_positions(callback_data.category_id)
    await edit_or_send(
        callback,
        f"Позиция удалена.\n\n{_positions_title(category)}",
        admin_kb.positions_list_kb(positions, category["id"], category["group_id"]),
    )
    await callback.answer("Позиция удалена")


# --- редактирование отдельных полей -----------------------------------------

_FIELD_STATE = {
    "edit_title": (AdminStates.waiting_position_title, "Введите новое название позиции:"),
    "edit_composition": (AdminStates.waiting_position_composition, "Введите состав (например: тесто, сыр, томаты):"),
    "edit_description": (AdminStates.waiting_position_description, "Введите описание позиции:"),
    "edit_allergens": (AdminStates.waiting_position_allergens, "Введите аллергены (например: глютен, молоко, орехи):"),
    "edit_served": (AdminStates.waiting_position_served, "Введите, с чем подаётся позиция:"),
}


@admin_router.callback_query(AdminPositionsCB.filter(F.action.in_(_FIELD_STATE.keys())))
async def cb_position_edit_field(callback: CallbackQuery, callback_data: AdminPositionsCB, state: FSMContext) -> None:
    target_state, prompt = _FIELD_STATE[callback_data.action]
    await state.set_state(target_state)
    await state.update_data(position_id=callback_data.id, category_id=callback_data.category_id, editing=True)
    await edit_or_send(callback, prompt, admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminPositionsCB.filter(F.action == "edit_photo"))
async def cb_position_edit_photo(callback: CallbackQuery, callback_data: AdminPositionsCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_position_photo)
    await state.update_data(position_id=callback_data.id, category_id=callback_data.category_id)
    await edit_or_send(
        callback,
        "Пришлите фото для позиции.\nЧтобы убрать текущее фото — отправьте «-».",
        admin_kb.cancel_kb(),
    )
    await callback.answer()


@admin_router.message(AdminStates.waiting_position_title)
async def on_position_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return
    data = await state.get_data()
    await state.clear()

    if data.get("editing") and data.get("position_id"):
        await db.update_position(data["position_id"], title=title)
        position_id = data["position_id"]
        await message.answer("Название обновлено ✅")
    else:
        position_id = await db.add_position(data["category_id"], title)
        await message.answer(
            "Позиция создана ✅\nТеперь заполните карточку: состав, описание, аллергены, с чем подаётся, и фото."
        )

    await _send_position_card(message, position_id)


@admin_router.message(AdminStates.waiting_position_composition)
async def on_position_composition(message: Message, state: FSMContext) -> None:
    text = (message.html_text or message.text or "").strip()
    data = await state.get_data()
    await db.update_position(data["position_id"], composition=text)
    await state.clear()
    await message.answer("Состав обновлён ✅")
    await _send_position_card(message, data["position_id"])


@admin_router.message(AdminStates.waiting_position_description)
async def on_position_description(message: Message, state: FSMContext) -> None:
    text = (message.html_text or message.text or "").strip()
    data = await state.get_data()
    await db.update_position(data["position_id"], description=text)
    await state.clear()
    await message.answer("Описание обновлено ✅")
    await _send_position_card(message, data["position_id"])


@admin_router.message(AdminStates.waiting_position_allergens)
async def on_position_allergens(message: Message, state: FSMContext) -> None:
    text = (message.html_text or message.text or "").strip()
    data = await state.get_data()
    await db.update_position(data["position_id"], allergens=text)
    await state.clear()
    await message.answer("Аллергены обновлены ✅")
    await _send_position_card(message, data["position_id"])


@admin_router.message(AdminStates.waiting_position_served)
async def on_position_served(message: Message, state: FSMContext) -> None:
    text = (message.html_text or message.text or "").strip()
    data = await state.get_data()
    await db.update_position(data["position_id"], served_with=text)
    await state.clear()
    await message.answer("Поле «с чем подаётся» обновлено ✅")
    await _send_position_card(message, data["position_id"])


@admin_router.message(AdminStates.waiting_position_photo, F.photo)
async def on_position_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    file_id = message.photo[-1].file_id
    await db.update_position(data["position_id"], photo_file_id=file_id)
    await state.clear()
    await message.answer("Фото обновлено ✅")
    await _send_position_card(message, data["position_id"])


@admin_router.message(AdminStates.waiting_position_photo, F.text)
async def on_position_photo_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    if text not in CLEAR_WORDS:
        await message.answer(
            "Пришлите фото или «-», чтобы убрать текущее фото.", reply_markup=admin_kb.cancel_kb()
        )
        return
    data = await state.get_data()
    await db.update_position(data["position_id"], photo_file_id=None)
    await state.clear()
    await message.answer("Фото удалено ✅")
    await _send_position_card(message, data["position_id"])


@admin_router.message(AdminStates.waiting_position_photo)
async def on_position_photo_other(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Не получилось распознать сообщение. Пришлите фото или «-», чтобы убрать текущее фото.",
        reply_markup=admin_kb.cancel_kb(),
    )
