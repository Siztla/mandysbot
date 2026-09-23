"""Форматирование карточек (все сообщения бота идут в HTML-режиме).

Позиции меню: поля хранятся в базе обычным текстом и экранируются здесь,
при сборке карточки; подписи полей выделяются жирным, поэтому произвольные
символы (<, >, &) ничего не ломают.

Пункты «Ценности»/«Стандарты» и онбординг: описание хранится в базе уже
готовым HTML (с жирным, курсивом, цитатами — см. utils.htmlsafe и миграцию в
database.db) и вставляется как есть; экранируется только заголовок.

Формат карточки повторяет файл «Завтраки»:
    Состав → Подача → Особенности → Описание для гостя
и дальше, если заполнены: Описание, Аллергены, С чем подаётся.
"""

import re
from html import escape

from utils.htmlsafe import esc

POSITION_PARSE_MODE = "HTML"

# «Соус: …», «Украшение: …» в начале строки — подпись внутри поля
_SUBLABEL_RE = re.compile(r"^([А-ЯЁA-Zа-яёa-z][А-ЯЁA-Zа-яёa-z \-]{0,29}):\s*(.*)$")


def _render_lines(value: str) -> list[str]:
    out = []
    for line in value.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = _SUBLABEL_RE.match(line)
        if m:
            out.append(f"<b>{escape(m.group(1).strip())}:</b> {escape(m.group(2))}")
        else:
            out.append(escape(line))
    return out


def _field(emoji: str, label: str, value: str) -> str:
    lines = _render_lines(value)
    if not lines:
        return ""
    header = f"{emoji} <b>{label}:</b>"
    # если первая строка сама с подписью («Основа: …») — начинаем с новой строки
    if lines[0].startswith(("<b>", "•")):
        return header + "\n" + "\n".join(lines)
    return header + " " + "\n".join(lines)


def _col(position, key: str) -> str:
    try:
        return position[key] or ""
    except (KeyError, IndexError):
        return ""


def format_position(position) -> str:
    title = position["title"]
    prefix = "" if title[:1] and not title[:1].isalnum() else "🍽 "
    parts = [f"{prefix}<b>{escape(title)}</b>"]

    guest = _col(position, "guest_description").strip()
    fields = [
        _field("🧾", "Состав", _col(position, "composition")),
        _field("🍴", "Подача", _col(position, "serving")),
        _field("✨", "Особенности", _col(position, "features")),
        (f"💬 <b>Описание для гостя:</b>\n<blockquote>{escape(guest)}</blockquote>" if guest else ""),
        _field("📋", "Описание", _col(position, "description")),
        _field("⚠️", "Аллергены", _col(position, "allergens")),
        _field("🥂", "С чем подаётся", _col(position, "served_with")),
    ]
    fields = [f for f in fields if f]
    if not fields:
        fields = ["Карточка пока не заполнена."]
    return "\n\n".join(parts + fields)


def format_position_admin(position) -> str:
    text = format_position(position)
    has_photo = "есть" if position["photo_file_id"] else "нет"
    return f"{text}\n\n— — —\nФото: {has_photo}"


def format_section_item(item) -> str:
    title = esc(item["title"])
    description = item["description"] or "Описание пока не добавлено."
    return f"<b>{title}</b>\n\n{description}"
