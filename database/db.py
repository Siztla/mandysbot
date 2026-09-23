"""
Слой работы с базой данных (SQLite через aiosqlite).

Структура:
    onboarding      — единственная запись с текстом приветствия и фото
    section_items   — пункты разделов "Ценности" и "Стандарты"
    groups          — группы меню (Завтраки, Бизнес ланч, ...)
    categories      — категории внутри группы
    positions       — позиции (блюда) внутри категории
    admins          — администраторы бота (user_id Telegram)
    quiz_questions  — вопросы теста по стандартам сервиса
    quiz_options    — варианты ответов к вопросам (один правильный)
    quiz_results    — результаты прохождения теста сотрудниками
    meta            — служебное key-value хранилище (флаги миграций и т.п.)
"""

import os
import time
from typing import Any, Optional

import aiosqlite

import config
from utils.htmlsafe import esc

DEFAULT_GROUPS = [
    "Завтраки",
    "Бизнес ланч",
    "To share",
    "Закуски",
    "Сэндвичи",
    "Салаты",
    "Супы",
    "Паста & ризотто",
    "Мясо & птица",
    "Рыба & морепродукты",
    "Овощи & гарниры",
    "Десерты",
    "Чай",
    "Кофе",
    "Лимонады",
    "Софт",
]

DEFAULT_ONBOARDING_TEXT = (
    "Добро пожаловать в команду Caffé Mandy's! 🥐☕\n\n"
    "Мы — ресторан-брассери с контактным баром на Покровке, в историческом "
    "доме с колосьями — первом в Москве здании в стиле модерн. Идея "
    "проекта: классическое нью-йоркское брассери, где смешиваются кухни и "
    "культуры мира, а лёгкость итальянского caffe уравновешивает энергию "
    "мегаполиса.\n\n"
    "Здесь одинаково уместны завтрак с детьми, деловой обед, ужин с "
    "друзьями и коктейль у барной стойки — в любое время суток гость "
    "должен чувствовать: здесь всё продумано, от приветствия до подачи "
    "блюда.\n\n"
    "Мы не просто кормим — мы дарим гостям кусочек Нью-Йорка, не покидая "
    "Москвы. И каждый из нас — часть этой истории.\n\n"
    "Дальше в этом боте — наши ценности, стандарты работы и полное меню. "
    "Добро пожаловать в команду! 🦫🍴"
)


async def get_conn() -> aiosqlite.Connection:
    db_dir = os.path.dirname(config.DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = await aiosqlite.connect(config.DB_PATH)
    await conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    conn = await get_conn()
    try:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS onboarding (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                text TEXT NOT NULL,
                photo_file_id TEXT
            );

            CREATE TABLE IF NOT EXISTS section_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT NOT NULL CHECK (section IN ('values', 'standards')),
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                photo_file_id TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                photo_file_id TEXT,
                composition TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                allergens TEXT NOT NULL DEFAULT '',
                served_with TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quiz_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
                option_text TEXT NOT NULL,
                is_correct INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                finished_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        await conn.commit()

        # --- сиды ---
        cur = await conn.execute("SELECT COUNT(*) AS c FROM groups")
        row = await cur.fetchone()
        if row["c"] == 0:
            now = int(time.time())
            for i, title in enumerate(DEFAULT_GROUPS):
                await conn.execute(
                    "INSERT INTO groups (title, sort_order, created_at) VALUES (?, ?, ?)",
                    (title, i, now),
                )
            await conn.commit()

        cur = await conn.execute("SELECT COUNT(*) AS c FROM onboarding")
        row = await cur.fetchone()
        if row["c"] == 0:
            await conn.execute(
                "INSERT INTO onboarding (id, text, photo_file_id) VALUES (1, ?, NULL)",
                (DEFAULT_ONBOARDING_TEXT,),
            )
            await conn.commit()

        for admin_id in config.ADMIN_IDS:
            await conn.execute(
                "INSERT OR IGNORE INTO admins (user_id, added_at) VALUES (?, ?)",
                (admin_id, int(time.time())),
            )
        await conn.commit()

        # --- одноразовая миграция: экранирование HTML-спецсимволов в уже
        # накопленном тексте, чтобы после перехода на parse_mode=HTML он
        # по-прежнему отображался как обычный текст, а не ломал разметку ---
        cur = await conn.execute("SELECT value FROM meta WHERE key = 'html_migration_v1'")
        row = await cur.fetchone()
        if row is None or row["value"] != "done":
            cur = await conn.execute("SELECT id, text FROM onboarding")
            for r in await cur.fetchall():
                await conn.execute(
                    "UPDATE onboarding SET text = ? WHERE id = ?",
                    (esc(r["text"]), r["id"]),
                )

            cur = await conn.execute("SELECT id, description FROM section_items")
            for r in await cur.fetchall():
                await conn.execute(
                    "UPDATE section_items SET description = ? WHERE id = ?",
                    (esc(r["description"]), r["id"]),
                )

            cur = await conn.execute(
                "SELECT id, composition, description, allergens, served_with FROM positions"
            )
            for r in await cur.fetchall():
                await conn.execute(
                    "UPDATE positions SET composition = ?, description = ?, allergens = ?, served_with = ? "
                    "WHERE id = ?",
                    (
                        esc(r["composition"]),
                        esc(r["description"]),
                        esc(r["allergens"]),
                        esc(r["served_with"]),
                        r["id"],
                    ),
                )

            await conn.execute(
                "INSERT INTO meta (key, value) VALUES ('html_migration_v1', 'done') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )
            await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Meta (служебное key-value хранилище)
# ---------------------------------------------------------------------------

async def get_meta(key: str) -> Optional[str]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else None
    finally:
        await conn.close()


async def set_meta(key: str, value: str) -> None:
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

async def get_onboarding() -> aiosqlite.Row:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM onboarding WHERE id = 1")
        return await cur.fetchone()
    finally:
        await conn.close()


async def update_onboarding(text: Optional[str] = None, photo_file_id: Optional[Any] = "__skip__") -> None:
    conn = await get_conn()
    try:
        if text is not None:
            await conn.execute("UPDATE onboarding SET text = ? WHERE id = 1", (text,))
        if photo_file_id != "__skip__":
            await conn.execute("UPDATE onboarding SET photo_file_id = ? WHERE id = 1", (photo_file_id,))
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Section items (values / standards)
# ---------------------------------------------------------------------------

async def get_section_items(section: str) -> list[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT * FROM section_items WHERE section = ? ORDER BY sort_order, id",
            (section,),
        )
        return await cur.fetchall()
    finally:
        await conn.close()


async def get_section_item(item_id: int) -> Optional[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM section_items WHERE id = ?", (item_id,))
        return await cur.fetchone()
    finally:
        await conn.close()


async def add_section_item(section: str, title: str, description: str = "", photo_file_id: Optional[str] = None) -> int:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM section_items WHERE section = ?", (section,))
        sort_order = (await cur.fetchone())["n"]
        cur = await conn.execute(
            "INSERT INTO section_items (section, title, description, photo_file_id, sort_order, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (section, title, description, photo_file_id, sort_order, int(time.time())),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def update_section_item(item_id: int, **fields) -> None:
    if not fields:
        return
    conn = await get_conn()
    try:
        keys = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [item_id]
        await conn.execute(f"UPDATE section_items SET {keys} WHERE id = ?", values)
        await conn.commit()
    finally:
        await conn.close()


async def delete_section_item(item_id: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM section_items WHERE id = ?", (item_id,))
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

async def get_groups() -> list[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM groups ORDER BY sort_order, id")
        return await cur.fetchall()
    finally:
        await conn.close()


async def get_group(group_id: int) -> Optional[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
        return await cur.fetchone()
    finally:
        await conn.close()


async def add_group(title: str) -> int:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM groups")
        sort_order = (await cur.fetchone())["n"]
        cur = await conn.execute(
            "INSERT INTO groups (title, sort_order, created_at) VALUES (?, ?, ?)",
            (title, sort_order, int(time.time())),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def update_group(group_id: int, title: str) -> None:
    conn = await get_conn()
    try:
        await conn.execute("UPDATE groups SET title = ? WHERE id = ?", (title, group_id))
        await conn.commit()
    finally:
        await conn.close()


async def delete_group(group_id: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

async def get_categories(group_id: int) -> list[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT * FROM categories WHERE group_id = ? ORDER BY sort_order, id", (group_id,)
        )
        return await cur.fetchall()
    finally:
        await conn.close()


async def get_category(category_id: int) -> Optional[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        return await cur.fetchone()
    finally:
        await conn.close()


async def add_category(group_id: int, title: str) -> int:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM categories WHERE group_id = ?", (group_id,)
        )
        sort_order = (await cur.fetchone())["n"]
        cur = await conn.execute(
            "INSERT INTO categories (group_id, title, sort_order, created_at) VALUES (?, ?, ?, ?)",
            (group_id, title, sort_order, int(time.time())),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def update_category(category_id: int, title: str) -> None:
    conn = await get_conn()
    try:
        await conn.execute("UPDATE categories SET title = ? WHERE id = ?", (title, category_id))
        await conn.commit()
    finally:
        await conn.close()


async def delete_category(category_id: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

async def get_positions(category_id: int) -> list[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT * FROM positions WHERE category_id = ? ORDER BY sort_order, id", (category_id,)
        )
        return await cur.fetchall()
    finally:
        await conn.close()


async def get_position(position_id: int) -> Optional[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
        return await cur.fetchone()
    finally:
        await conn.close()


async def add_position(category_id: int, title: str) -> int:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM positions WHERE category_id = ?", (category_id,)
        )
        sort_order = (await cur.fetchone())["n"]
        cur = await conn.execute(
            "INSERT INTO positions (category_id, title, sort_order, created_at) VALUES (?, ?, ?, ?)",
            (category_id, title, sort_order, int(time.time())),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def update_position(position_id: int, **fields) -> None:
    if not fields:
        return
    conn = await get_conn()
    try:
        keys = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [position_id]
        await conn.execute(f"UPDATE positions SET {keys} WHERE id = ?", values)
        await conn.commit()
    finally:
        await conn.close()


async def delete_position(position_id: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Admins
# ---------------------------------------------------------------------------

async def get_admin_ids() -> set[int]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        return {r["user_id"] for r in rows}
    finally:
        await conn.close()


async def add_admin(user_id: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_at) VALUES (?, ?)",
            (user_id, int(time.time())),
        )
        await conn.commit()
    finally:
        await conn.close()


async def remove_admin(user_id: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Тест по стандартам: вопросы и варианты ответов
# ---------------------------------------------------------------------------

async def get_quiz_questions() -> list[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM quiz_questions ORDER BY sort_order, id")
        return await cur.fetchall()
    finally:
        await conn.close()


async def count_quiz_questions() -> int:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT COUNT(*) AS c FROM quiz_questions")
        row = await cur.fetchone()
        return row["c"]
    finally:
        await conn.close()


async def get_quiz_question(question_id: int) -> Optional[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM quiz_questions WHERE id = ?", (question_id,))
        return await cur.fetchone()
    finally:
        await conn.close()


async def add_quiz_question(question: str) -> int:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM quiz_questions")
        sort_order = (await cur.fetchone())["n"]
        cur = await conn.execute(
            "INSERT INTO quiz_questions (question, sort_order, created_at) VALUES (?, ?, ?)",
            (question, sort_order, int(time.time())),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def update_quiz_question(question_id: int, question: str) -> None:
    conn = await get_conn()
    try:
        await conn.execute("UPDATE quiz_questions SET question = ? WHERE id = ?", (question, question_id))
        await conn.commit()
    finally:
        await conn.close()


async def delete_quiz_question(question_id: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM quiz_questions WHERE id = ?", (question_id,))
        await conn.commit()
    finally:
        await conn.close()


async def get_quiz_options(question_id: int) -> list[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT * FROM quiz_options WHERE question_id = ? ORDER BY sort_order, id", (question_id,)
        )
        return await cur.fetchall()
    finally:
        await conn.close()


async def get_quiz_option(option_id: int) -> Optional[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT * FROM quiz_options WHERE id = ?", (option_id,))
        return await cur.fetchone()
    finally:
        await conn.close()


async def replace_quiz_options(question_id: int, options: list[tuple[str, bool]]) -> None:
    """Полностью заменяет варианты ответа вопроса: удаляет старые, пишет
    новые. `options` — список (текст_варианта, это_правильный)."""
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM quiz_options WHERE question_id = ?", (question_id,))
        for i, (text, is_correct) in enumerate(options):
            await conn.execute(
                "INSERT INTO quiz_options (question_id, option_text, is_correct, sort_order) "
                "VALUES (?, ?, ?, ?)",
                (question_id, text, 1 if is_correct else 0, i),
            )
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Тест по стандартам: результаты прохождения
# ---------------------------------------------------------------------------

async def save_quiz_result(user_id: int, user_name: str, score: int, total: int) -> None:
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO quiz_results (user_id, user_name, score, total, finished_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, user_name, score, total, int(time.time())),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_quiz_results(limit: int = 50) -> list[aiosqlite.Row]:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT * FROM quiz_results ORDER BY finished_at DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()
    finally:
        await conn.close()
