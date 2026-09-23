from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from utils.access import is_admin


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return await is_admin(user.id)
