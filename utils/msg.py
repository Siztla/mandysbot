"""Вспомогательные функции для редактирования/пересоздания сообщений
при переходах по инлайн-меню."""

from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup


async def edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Обновляет текстовое сообщение (списки, меню). Если исходное
    сообщение было с фото — пересоздаёт как обычный текст."""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=reply_markup)


async def show_card(
    callback: CallbackQuery,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Показывает карточку, которая может содержать фото (позиция, пункт
    раздела, онбординг). Всегда пересоздаёт сообщение, чтобы корректно
    переключаться между текстовым и фото-форматом."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    if photo_file_id:
        caption = text if len(text) <= 1024 else text[:1021] + "…"
        await callback.message.answer_photo(photo=photo_file_id, caption=caption, reply_markup=reply_markup)
    else:
        await callback.message.answer(text, reply_markup=reply_markup)
