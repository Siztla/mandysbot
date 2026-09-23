from aiogram import Router

from utils.filters import IsAdmin

# Общий роутер админ-части. Фильтр IsAdmin применяется только к callback_query
# — команда /admin и FSM-хендлеры проверяют доступ самостоятельно (состояние
# FSM привязано к конкретному пользователю, который уже прошёл проверку на
# предыдущем шаге через callback).
admin_router = Router(name="admin")
admin_router.callback_query.filter(IsAdmin())

# Подмодули регистрируют свои хендлеры на admin_router через импорт.
from handlers.admin import root  # noqa: E402,F401
from handlers.admin import groups  # noqa: E402,F401
from handlers.admin import categories  # noqa: E402,F401
from handlers.admin import positions  # noqa: E402,F401
from handlers.admin import sections  # noqa: E402,F401
from handlers.admin import onboarding  # noqa: E402,F401
from handlers.admin import admins  # noqa: E402,F401

__all__ = ["admin_router"]
