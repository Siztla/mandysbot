"""Вспомогательные функции для редактирования/пересоздания сообщений
при переходах по инлайн-меню.

Все тексты бота отправляются в HTML-режиме (parse_mode="HTML" — по
умолчанию у бота и у функций ниже). Текст никогда не обрезается:

* подпись к фото в Telegram — максимум 1024 видимых символа. Если карточка
  длиннее, она отправляется двумя сообщениями: фото (подпись — только первая
  строка карточки) и следом полный текст с кнопками. Фото-«компаньон»
  запоминается и удаляется, когда пользователь уходит с карточки, чтобы в
  чате не копились старые фото;
* сообщение в Telegram — максимум 4096 символов. Более длинный текст
  делится на несколько сообщений по границам абзацев, кнопки — у последнего.

Если Telegram не смог разобрать HTML-разметку (например, в старом тексте
остался «голый» символ <), сообщение повторяется без разметки, чтобы
сотрудник в любом случае увидел текст.
"""

import logging
import re
from html import unescape
from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)

HTML = "HTML"
CAPTION_LIMIT = 1024
MESSAGE_LIMIT = 4096

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


def visible_length(text: str, parse_mode: Optional[str] = HTML) -> int:
    """Длина текста так, как её считает Telegram: без HTML-тегов и в
    единицах UTF-16 (эмодзи = 2)."""
    if parse_mode and parse_mode.upper() == HTML:
        text = unescape(re.sub(r"<[^>]+>", "", text))
    return len(text.encode("utf-16-le")) // 2


def _caption_head(text: str, parse_mode: Optional[str]) -> str:
    """Короткая подпись к фото, когда полный текст идёт отдельным сообщением.
    Берётся первая строка, только если в ней нет незакрытых тегов."""
    first = text.split("\n", 1)[0]
    if parse_mode and parse_mode.upper() == HTML:
        opened = re.findall(r"<([a-z]+)[^>]*>", first)
        closed = re.findall(r"</([a-z]+)>", first)
        if sorted(opened) != sorted(closed):
            return ""
    return first if visible_length(first, parse_mode) <= CAPTION_LIMIT else ""


def _chunk_text(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    """Разбивает текст на части не длиннее `limit` символов. Режет по
    границам абзацев ("\\n\\n"), жадно упаковывая в каждую часть как можно
    больше абзацев. Если отдельный абзац сам длиннее `limit` — режет его
    по последнему пробелу перед границей (а если пробела нет — жёстко по
    границе)."""
    if len(text) <= limit:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        piece = para
        while len(piece) > limit:
            if current:
                chunks.append(current)
                current = ""
            cut = piece.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            chunks.append(piece[:cut])
            piece = piece[cut:].lstrip(" ")

        if not piece:
            continue

        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = piece

    if current:
        chunks.append(current)

    return chunks


def _looks_like_html_error(exc: TelegramBadRequest) -> bool:
    text = str(exc).lower()
    return "parse" in text or "entit" in text


async def _answer_safe(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup],
    parse_mode: Optional[str],
) -> Message:
    try:
        return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if parse_mode and _looks_like_html_error(e):
            logger.warning("Не удалось отправить сообщение как HTML (%s), повтор без разметки", e)
            return await message.answer(text, reply_markup=reply_markup, parse_mode=None)
        raise


async def _answer_photo_safe(
    message: Message,
    photo_file_id: str,
    caption: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup],
    parse_mode: Optional[str],
) -> Message:
    try:
        return await message.answer_photo(
            photo=photo_file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode
        )
    except TelegramBadRequest as e:
        if parse_mode and caption and _looks_like_html_error(e):
            logger.warning("Не удалось отправить подпись к фото как HTML (%s), повтор без разметки", e)
            return await message.answer_photo(
                photo=photo_file_id, caption=caption, reply_markup=reply_markup, parse_mode=None
            )
        raise


async def _answer_text(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup],
    parse_mode: Optional[str],
) -> Message:
    """Отправляет текст любой длины: при необходимости несколькими
    сообщениями, кнопки — у последнего. Возвращает последнее сообщение."""
    chunks = _chunk_text(text)
    sent: Optional[Message] = None
    for i, chunk in enumerate(chunks):
        kb = reply_markup if i == len(chunks) - 1 else None
        sent = await _answer_safe(message, chunk, kb, parse_mode)
    return sent


async def send_card(
    target: Message,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = HTML,
) -> Message:
    """Отправляет карточку в чат сообщения `target` (без удаления
    исходного). Возвращает сообщение с кнопками (текстовое или фото)."""
    if not photo_file_id:
        return await _answer_text(target, text, reply_markup, parse_mode)

    if visible_length(text, parse_mode) <= CAPTION_LIMIT:
        return await _answer_photo_safe(target, photo_file_id, text, reply_markup, parse_mode)

    photo_msg = await _answer_photo_safe(
        target, photo_file_id, _caption_head(text, parse_mode) or None, None, parse_mode
    )
    text_msg = await _answer_text(target, text, reply_markup, parse_mode)
    _photo_companions[(text_msg.chat.id, text_msg.message_id)] = photo_msg.message_id
    return text_msg


async def edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = HTML,
) -> None:
    """Обновляет текстовое сообщение (списки, меню). Если исходное
    сообщение было с фото (или текст слишком длинный для одного
    сообщения) — пересоздаёт его."""
    await _drop_companion(callback.message)
    if len(text) <= MESSAGE_LIMIT:
        try:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
            if parse_mode and _looks_like_html_error(e):
                logger.warning("Не удалось отредактировать сообщение как HTML (%s), повтор без разметки", e)
                try:
                    await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=None)
                    return
                except TelegramBadRequest:
                    pass
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _answer_text(callback.message, text, reply_markup, parse_mode)


async def show_card(
    callback: CallbackQuery,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = HTML,
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
