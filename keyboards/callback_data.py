"""Типизированные callback_data фабрики для инлайн-кнопок."""

from aiogram.filters.callback_data import CallbackData


# --- Пользовательская часть -------------------------------------------------

class MainCB(CallbackData, prefix="mm"):
    action: str  # "root" | "values" | "standards" | "menu"


class SectionCB(CallbackData, prefix="sc"):
    section: str  # "values" | "standards"
    action: str   # "list" | "view"
    id: int = 0


class MenuCB(CallbackData, prefix="mn"):
    action: str  # "groups" | "group" | "category" | "position"
    id: int = 0


# --- Админ-часть -------------------------------------------------------------

class AdminRootCB(CallbackData, prefix="ar"):
    action: str  # "root" | "menu" | "values" | "standards" | "onboarding" | "admins" | "exit"


class AdminGroupsCB(CallbackData, prefix="ag"):
    action: str  # "list" | "open" | "add" | "rename" | "delete"
    id: int = 0


class AdminCategoriesCB(CallbackData, prefix="ac"):
    action: str  # "list" | "open" | "add" | "rename" | "delete"
    group_id: int = 0
    id: int = 0


class AdminPositionsCB(CallbackData, prefix="ap"):
    action: str
    # "list" | "open" | "add" | "delete" | "preview" |
    # "edit_title" | "edit_photo" | "edit_composition" |
    # "edit_description" | "edit_allergens" | "edit_served"
    category_id: int = 0
    id: int = 0


class AdminSectionCB(CallbackData, prefix="asc"):
    section: str  # "values" | "standards"
    action: str   # "list" | "open" | "add" | "rename" | "edit_desc" | "edit_photo" | "delete"
    id: int = 0


class AdminOnboardingCB(CallbackData, prefix="ao"):
    action: str  # "open" | "edit_text" | "edit_photo"


class AdminAdminsCB(CallbackData, prefix="aa"):
    action: str  # "list" | "add" | "remove"
    id: int = 0


ADMIN_CANCEL = "admin:cancel"
