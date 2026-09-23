import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database.db import init_db
from handlers.user import router as user_router
from handlers.quiz import router as quiz_router
from handlers.admin import admin_router


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not config.BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не задан. Создайте файл .env на основе .env.example и укажите токен бота."
        )

    await init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важен: сначала админ-роутер (у него есть команда /admin и все
    # admin:*-колбэки), затем пользовательский. Хендлеры не пересекаются по
    # callback_data-префиксам, так что порядок на работу не влияет, но так
    # нагляднее.
    dp.include_router(admin_router)
    dp.include_router(quiz_router)
    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Mandy's training bot запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
