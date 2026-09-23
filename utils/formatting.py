"""Форматирование карточек для отправки в HTML-режиме. Заголовки
(title) — обычный текст, который экранируется здесь перед вставкой;
описательные поля (composition/description/allergens/served_with)
приходят из БД уже безопасными для HTML (см. utils.htmlsafe и миграцию
в database.db) и вставляются как есть, без повторного экранирования."""

from utils.htmlsafe import esc


def format_position(position) -> str:
    lines = [f"🍽 {esc(position['title'])}"]

    if position["composition"]:
        lines.append(f"\n🧾 Состав:\n{position['composition']}")
    if position["description"]:
        lines.append(f"\n📋 Описание:\n{position['description']}")
    if position["allergens"]:
        lines.append(f"\n⚠️ Аллергены:\n{position['allergens']}")
    if position["served_with"]:
        lines.append(f"\n🍴 С чем подаётся:\n{position['served_with']}")

    if len(lines) == 1:
        lines.append("\nКарточка пока не заполнена.")

    return "\n".join(lines)


def format_position_admin(position) -> str:
    text = format_position(position)
    has_photo = "есть" if position["photo_file_id"] else "нет"
    return f"{text}\n\n— — —\nФото: {has_photo}"


def format_section_item(item) -> str:
    title = esc(item["title"])
    description = item["description"] or "Описание пока не добавлено."
    return f"{title}\n\n{description}"
