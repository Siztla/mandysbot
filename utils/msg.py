"""Вспомогательные функции для редактирования/пересоздания сообщений
при переходах по инлайн-меню."""

import logging
from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)


def _chunk_text(text: str, limit: int = 4096) -> list[str]:
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


async def _edit_text_safe(message: Message, text: str, reply_markup: Optional[InlineKeyboardMarkup]) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if _looks_like_html_error(e):
            logger.warning("Не удалось отредактировать сообщение как HTML (%s), повтор без разметки", e)
            await message.edit_text(text, reply_markup=reply_markup, parse_mode=None)
        else:
            raise


async def _answer_safe(message: Message, text: str, reply_markup: Optional[InlineKeyboardMarkup]) -> None:
    try:
        await message.answer(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if _looks_like_html_error(e):
            logger.warning("Не удалось отправить сообщение как HTML (%s), повтор без разметки", e)
            await message.answer(text, reply_markup=reply_markup, parse_mode=None)
        else:
            raise


async def _answer_photo_safe(
    message: Message,
    photo_file_id: str,
    caption: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup],
) -> None:
    try:
        await message.answer_photo(photo=photo_file_id, caption=caption, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if _looks_like_html_error(e):
            logger.warning("Не удалось отправить фото-подпись как HTML (%s), повтор без разметки", e)
            await message.answer_photo(
                photo=photo_file_id, caption=caption, reply_markup=reply_markup, parse_mode=None
            )
        else:
            raise


async def _deliver_card(
    message: Message,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup],
) -> None:
    """Отправляет карточку (фото+подпись или просто текст) сообщением
    `message.answer*`, без обрезания текста: длинную подпись/текст при
    необходимости разбивает на несколько сообщений."""
    if photo_file_id:
        if len(text) > 1024:
            await _answer_photo_safe(message, photo_file_id, None, None)
            chunks = _chunk_text(text)
            for i, chunk in enumerate(chunks):
                kb = reply_markup if i == len(chunks) - 1 else None
                await _answer_safe(message, chunk, kb)
        else:
            await _answer_photo_safe(message, photo_file_id, text, reply_markup)
    else:
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            kb = reply_markup if i == len(chunks) - 1 else None
            await _answer_safe(message, chunk, kb)


async def edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Обновляет текстовое сообщение (списки, меню). Если исходное
    сообщение было с фото — пересоздаёт как обычный текст."""
    try:
        await _edit_text_safe(callback.message, text, reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        try:
            await callback.message.delete()
        except Exception:
            pass
        await _answer_safe(callback.message, text, reply_markup)


async def show_card(
    callback: CallbackQuery,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Показывает карточку, которая может содержать фото (позиция, пункт
    раздела, онбординг). Всегда пересоздаёт сообщение, чтобы корректно
    переключаться между текстовым и фото-форматом. Текст никогда не
    обрезается: если подпись к фото не помещается в лимит Telegram (1024
    символа), фото отправляется без подписи, а следом — отдельным
    сообщением полный текст."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _deliver_card(callback.message, text, photo_file_id, reply_markup)


async def send_card(
    message: Message,
    text: str,
    photo_file_id: Optional[str],
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """То же самое, что show_card, но в ответ на обычное сообщение (а не
    колбэк с существующей карточкой для замены) — без удаления/
    пересоздания. Используется в message-хендлерах после создания/
    редактирования записи."""
    await _deliver_card(message, text, photo_file_id, reply_markup)
