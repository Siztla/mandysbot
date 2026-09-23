"""Админ-управление тестом по стандартам: вопросы, варианты ответов,
результаты прохождения сотрудниками."""

from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import db
from handlers.admin import admin_router
from keyboards import admin_kb
from keyboards.callback_data import AdminRootCB, AdminQuizCB
from states.admin_states import AdminStates
from utils.htmlsafe import esc
from utils.msg import edit_or_send

LIST_TITLE = "🧪 Тест по стандартам сервиса\n\nВопросы:"

OPTIONS_HELP = (
    "Отправьте варианты ответа — каждый с новой строки. Отметьте "
    "ПРАВИЛЬНЫЙ вариант звёздочкой (*) в начале строки. Нужно минимум "
    "2 варианта, и правильный должен быть ровно один.\n\n"
    "Например:\n"
    "*Обязательно поздороваться и предложить меню\n"
    "Молча проводить к столу\n"
    "Подождать, пока гость сам позовёт"
)


def _question_card_text(question, options) -> str:
    lines = [f"❓ {esc(question['question'])}", ""]
    for opt in options:
        mark = "✅" if opt["is_correct"] else "▫️"
        lines.append(f"{mark} {esc(opt['option_text'])}")
    if not options:
        lines.append("(варианты ответа ещё не заданы)")
    return "\n".join(lines)


async def _send_question_card(message: Message, question_id: int) -> None:
    question = await db.get_quiz_question(question_id)
    options = await db.get_quiz_options(question_id)
    await message.answer(
        _question_card_text(question, options),
        reply_markup=admin_kb.quiz_question_card_kb(question_id),
    )


def _parse_options(text: str):
    """Возвращает список (текст, правильный) или None, если формат неверный."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    options = []
    correct_count = 0
    for line in lines:
        if line.startswith("*"):
            options.append((line[1:].strip(), True))
            correct_count += 1
        else:
            options.append((line, False))
    if correct_count != 1:
        return None
    if any(not text for text, _ in options):
        return None
    return options


@admin_router.callback_query(AdminRootCB.filter(F.action == "quiz"))
async def cb_quiz_open(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    questions = await db.get_quiz_questions()
    await edit_or_send(callback, LIST_TITLE, admin_kb.quiz_list_kb(questions))
    await callback.answer()


@admin_router.callback_query(AdminQuizCB.filter(F.action == "list"))
async def cb_quiz_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    questions = await db.get_quiz_questions()
    await edit_or_send(callback, LIST_TITLE, admin_kb.quiz_list_kb(questions))
    await callback.answer()


@admin_router.callback_query(AdminQuizCB.filter(F.action == "open"))
async def cb_quiz_question_open(callback: CallbackQuery, callback_data: AdminQuizCB, state: FSMContext) -> None:
    await state.clear()
    question = await db.get_quiz_question(callback_data.id)
    if question is None:
        await callback.answer("Вопрос не найден.", show_alert=True)
        return
    options = await db.get_quiz_options(question["id"])
    await edit_or_send(
        callback,
        _question_card_text(question, options),
        admin_kb.quiz_question_card_kb(question["id"]),
    )
    await callback.answer()


@admin_router.callback_query(AdminQuizCB.filter(F.action == "add"))
async def cb_quiz_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_quiz_question_text)
    await state.update_data(editing=False)
    await edit_or_send(callback, "Введите текст нового вопроса:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminQuizCB.filter(F.action == "edit_text"))
async def cb_quiz_edit_text(callback: CallbackQuery, callback_data: AdminQuizCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_quiz_question_text)
    await state.update_data(editing=True, question_id=callback_data.id)
    await edit_or_send(callback, "Введите новый текст вопроса:", admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminQuizCB.filter(F.action == "edit_options"))
async def cb_quiz_edit_options(callback: CallbackQuery, callback_data: AdminQuizCB, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_quiz_options_text)
    await state.update_data(question_id=callback_data.id)
    await edit_or_send(callback, OPTIONS_HELP, admin_kb.cancel_kb())
    await callback.answer()


@admin_router.callback_query(AdminQuizCB.filter(F.action == "delete"))
async def cb_quiz_delete(callback: CallbackQuery, callback_data: AdminQuizCB, state: FSMContext) -> None:
    await db.delete_quiz_question(callback_data.id)
    questions = await db.get_quiz_questions()
    await edit_or_send(callback, f"Вопрос удалён.\n\n{LIST_TITLE}", admin_kb.quiz_list_kb(questions))
    await callback.answer("Вопрос удалён")


@admin_router.callback_query(AdminQuizCB.filter(F.action == "results"))
async def cb_quiz_results(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    results = await db.get_quiz_results(limit=30)
    if not results:
        text = "📊 Результаты теста\n\nПока никто не проходил тест."
    else:
        lines = [f"📊 Результаты теста (последние {len(results)}):", ""]
        for r in results:
            pct = round(100 * r["score"] / r["total"]) if r["total"] else 0
            dt = datetime.fromtimestamp(r["finished_at"]).strftime("%d.%m.%Y %H:%M")
            lines.append(f"{esc(r['user_name'])} — {r['score']}/{r['total']} ({pct}%) — {dt}")
        text = "\n".join(lines)
    await edit_or_send(callback, text, admin_kb.quiz_list_or_back_kb())
    await callback.answer()


@admin_router.message(AdminStates.waiting_quiz_question_text)
async def on_quiz_question_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст вопроса не может быть пустым. Попробуйте ещё раз:", reply_markup=admin_kb.cancel_kb())
        return

    data = await state.get_data()

    if data.get("editing") and data.get("question_id"):
        await db.update_quiz_question(data["question_id"], text)
        await state.clear()
        await message.answer("Текст вопроса обновлён ✅")
        await _send_question_card(message, data["question_id"])
        return

    question_id = await db.add_quiz_question(text)
    await state.set_state(AdminStates.waiting_quiz_options_text)
    await state.update_data(question_id=question_id)
    await message.answer("Вопрос создан ✅\n\n" + OPTIONS_HELP, reply_markup=admin_kb.cancel_kb())


@admin_router.message(AdminStates.waiting_quiz_options_text)
async def on_quiz_options_text(message: Message, state: FSMContext) -> None:
    options = _parse_options(message.text or "")
    if options is None:
        await message.answer(
            "Не получилось разобрать варианты. Нужно минимум 2 строки, и ровно "
            "одна должна начинаться с «*» (правильный вариант). Попробуйте ещё раз:\n\n"
            + OPTIONS_HELP,
            reply_markup=admin_kb.cancel_kb(),
        )
        return

    data = await state.get_data()
    question_id = data["question_id"]
    await db.replace_quiz_options(question_id, options)
    await state.clear()
    await message.answer("Варианты ответа сохранены ✅")
    await _send_question_card(message, question_id)
