"""Прохождение теста по стандартам сервиса сотрудником."""

import random

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from database import db
from keyboards import user_kb
from keyboards.callback_data import QuizCB
from states.quiz_states import QuizStates
from utils.htmlsafe import esc
from utils.msg import edit_or_send

router = Router(name="quiz")


def _user_display_name(user) -> str:
    name = " ".join(filter(None, [user.first_name, user.last_name]))
    if user.username:
        return f"{name} (@{user.username})".strip()
    return name or str(user.id)


async def _show_question(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    question_ids = data["question_ids"]
    index = data["index"]

    if index >= len(question_ids):
        await _finish_quiz(callback, state)
        return

    question = await db.get_quiz_question(question_ids[index])
    options = await db.get_quiz_options(question_ids[index])
    if question is None or len(options) < 2:
        # вопрос был удалён администратором прямо во время прохождения — пропускаем
        await state.update_data(index=index + 1)
        await _show_question(callback, state)
        return

    total = len(question_ids)
    text = f"Вопрос {index + 1} из {total}\n\n{esc(question['question'])}"
    await edit_or_send(callback, text, user_kb.quiz_question_kb(options))


async def _finish_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    score = data["score"]
    total = data["total"]
    user = callback.from_user

    await db.save_quiz_result(user.id, _user_display_name(user), score, total)
    await state.clear()

    percent = round(100 * score / total) if total else 0
    if percent == 100:
        verdict = "Отлично! Стандарты знаете назубок 🎉"
    elif percent >= 70:
        verdict = "Хороший результат, но кое-что стоит повторить 👍"
    else:
        verdict = "Стоит ещё раз внимательно перечитать стандарты 📖"

    text = f"Тест завершён!\n\nВаш результат: {score} из {total} ({percent}%)\n\n{verdict}"
    await edit_or_send(callback, text, user_kb.quiz_result_kb())


@router.callback_query(QuizCB.filter(F.action == "start"))
async def cb_quiz_start(callback: CallbackQuery, state: FSMContext) -> None:
    questions = await db.get_quiz_questions()
    # берём только вопросы, у которых реально есть варианты ответа
    valid_ids = []
    for q in questions:
        opts = await db.get_quiz_options(q["id"])
        if len(opts) >= 2:
            valid_ids.append(q["id"])

    if not valid_ids:
        await callback.answer("Тест пока не готов — вопросов нет.", show_alert=True)
        return

    random.shuffle(valid_ids)
    await state.set_state(QuizStates.taking)
    await state.update_data(question_ids=valid_ids, index=0, score=0, total=len(valid_ids))
    await callback.answer()
    await _show_question(callback, state)


@router.callback_query(QuizStates.taking, QuizCB.filter(F.action == "answer"))
async def cb_quiz_answer(callback: CallbackQuery, callback_data: QuizCB, state: FSMContext) -> None:
    option = await db.get_quiz_option(callback_data.id)
    data = await state.get_data()

    if option is None:
        await callback.answer()
        await state.update_data(index=data["index"] + 1)
        await _show_question(callback, state)
        return

    question = await db.get_quiz_question(option["question_id"])
    options = await db.get_quiz_options(option["question_id"])
    correct = next((o for o in options if o["is_correct"]), None)

    if option["is_correct"]:
        await callback.answer("✅ Верно!")
        new_score = data["score"] + 1
    else:
        correct_text = correct["option_text"] if correct else "?"
        await callback.answer(f"❌ Неверно. Правильный ответ: {correct_text}", show_alert=True)
        new_score = data["score"]

    await state.update_data(score=new_score, index=data["index"] + 1)
    await _show_question(callback, state)
