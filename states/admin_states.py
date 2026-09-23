from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    # группы
    waiting_group_title = State()
    waiting_group_rename = State()

    # категории
    waiting_category_title = State()
    waiting_category_rename = State()

    # позиции
    waiting_position_title = State()
    waiting_position_photo = State()
    waiting_position_composition = State()
    waiting_position_description = State()
    waiting_position_allergens = State()
    waiting_position_served = State()

    # пункты разделов "Ценности" / "Стандарты"
    waiting_section_title = State()
    waiting_section_rename = State()
    waiting_section_description = State()
    waiting_section_photo = State()
    waiting_section_bulk_import = State()

    # онбординг
    waiting_onboarding_text = State()
    waiting_onboarding_photo = State()

    # администраторы
    waiting_admin_id_add = State()

    # тест по стандартам
    waiting_quiz_question_text = State()
    waiting_quiz_options_text = State()
