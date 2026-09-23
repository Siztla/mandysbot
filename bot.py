import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database.db import init_db
from handlers.user import router as user_router
from handlers.quiz import router as quiz_router
from handlers.admin import admin_router
from tools.import_menu import auto_import


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not config.BOT_TOKEN:
        logging.error(
            "BOT_TOKEN не задан. Укажите его в переменных окружения хостинга "
            "(или в файле .env по образцу .env.example)."
        )
        return 1

    logging.info("Токен бота из окружения: %s", config.masked_token())

    await init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        try:
            me = await bot.get_me()
        except TelegramUnauthorizedError:
            logging.error(
                "Telegram отклонил токен %s (Unauthorized). Этот токен отозван или "
                "введён с ошибкой. Возьмите актуальный токен у @BotFather (/mytoken), "
                "пропишите его в BOT_TOKEN на хостинге и пересоздайте контейнер.",
                config.masked_token(),
            )
            # пауза, чтобы хостинг не перезапускал бота каждую секунду
            await asyncio.sleep(30)
            return 1
        logging.info("Токен принят Telegram: @%s", me.username)

        dp = Dispatcher(storage=MemoryStorage())

        # Порядок важен: сначала админ-роутер (у него есть команда /admin и все
        # admin:*-колбэки), затем пользовательский. Хендлеры не пересекаются по
        # callback_data-префиксам, так что порядок на работу не влияет, но так
        # нагляднее.
        dp.include_router(admin_router)
        dp.include_router(quiz_router)
        dp.include_router(user_router)

        await bot.delete_webhook(drop_pending_updates=True)

        # Если в data/menu/menu.json новое меню — загрузить его в базу (в фоне,
        # бот при этом уже отвечает пользователям).
        async def _safe_auto_import() -> None:
            try:
                await auto_import(bot)
            except Exception:
                logging.exception("Автоимпорт меню не удался")

        asyncio.create_task(_safe_auto_import())
        logging.info("Mandy's training bot запущен")
        await dp.start_polling(bot)
        return 0
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
        raise
