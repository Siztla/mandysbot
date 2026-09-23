"""Форматирование карточек в обычный текст (без разметки, чтобы не ломалось
на произвольном тексте, который вводит администратор)."""


def format_position(position) -> str:
    lines = [f"🍽 {position['title']}"]

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
    title = item["title"]
    description = item["description"] or "Описание пока не добавлено."
    return f"{title}\n\n{description}"
