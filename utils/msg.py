"""Вспомогательные функции для редактирования/пересоздания сообщений
при переходах по инлайн-меню.

Карточка с фото. Подпись к фото в Telegram — максимум 1024 символа.
Если текст длиннее, карточка отправляется двумя сообщениями: фото (подпись —
только первая строка карточки) и следом полный текст с кнопками. Текст
никогда не обрезается. Фото-«компаньон» запоминается и удаляется, когда
пользователь уходит с карточки, чтобы в чате не копились старые фото.
"""

import re
from html import unescape
from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

CAPTION_LIMIT = 1024

# (chat_id, id сообщения с текстом) -> id сообщения с фото
_photo_companions: dict[tuple[int, int], int] = {}


async def _drop_companion(message: Message) -> None:
    photo_id = _photo_companions.pop((message.chat.id, message.message_id), None)
    if photo_id is None:
        return
    try:
        await message.bot.delete_message(message.chat.id, photo_id)
    except Exception:
        pass


def visible_length(text: str, parse_mode: Optional[str] = None) -> int:
    """Длина текста так, как её считает Telegram: без HTML-тегов и в
    единицах UTF-16 (эмодзи = 2)."""
    if parse_mode and parse_mode.upper() == "HTML":
        text = unescape(re.sub(r"<[^>]+>", "", text))
    return len(text.encode("utf-16-le")) // 2


def _caption_head(text: str) -> str:
    """Короткая подпись к фото, когда полный текст идёт отдельным сообщением."""
    first = text.split("\n", 1)[0]
    return first if visible_length(first) <= CAPTION_LIMIT else ""


async def send_card(
    target: Message,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> Message:
    """Отправляет карточку в чат сообщения `target`. Возвращает сообщение с
    кнопками (текстовое или фото)."""
    if not photo_file_id:
        return await target.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

    if visible_length(text, parse_mode) <= CAPTION_LIMIT:
        return await target.answer_photo(
            photo=photo_file_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode
        )

    photo_msg = await target.answer_photo(
        photo=photo_file_id, caption=_caption_head(text) or None, parse_mode=parse_mode
    )
    text_msg = await target.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    _photo_companions[(text_msg.chat.id, text_msg.message_id)] = photo_msg.message_id
    return text_msg


async def edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> None:
    """Обновляет текстовое сообщение (списки, меню). Если исходное
    сообщение было с фото — пересоздаёт как обычный текст."""
    await _drop_companion(callback.message)
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


async def show_card(
    callback: CallbackQuery,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = None,
) -> None:
    """Показывает карточку, которая может содержать фото (позиция, пункт
    раздела, онбординг). Всегда пересоздаёт сообщение, чтобы корректно
    переключаться между текстовым и фото-форматом."""
    await _drop_companion(callback.message)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_card(callback.message, text, photo_file_id, reply_markup, parse_mode)
