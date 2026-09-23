from aiogram.fsm.state import State, StatesGroup


class QuizStates(StatesGroup):
    taking = State()  # сотрудник проходит тест; данные сессии — в FSMContext
