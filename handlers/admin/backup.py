from aiogram import F
from aiogram.types import CallbackQuery, FSInputFile
import os
from datetime import datetime

from handlers.admin import admin_router
from keyboards.callback_data import AdminRootCB
import config


@admin_router.callback_query(AdminRootCB.filter(F.action == "backup"))
async def cb_admin_backup(callback: CallbackQuery) -> None:
    if not os.path.exists(config.DB_PATH):
        await callback.answer("Файл базы данных не найден.", show_alert=True)
        return
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    doc = FSInputFile(config.DB_PATH, filename=f"mandys_backup_{ts}.db")
    await callback.message.answer_document(doc, caption=f"Резервная копия базы данных на {ts}")
    await callback.answer()
