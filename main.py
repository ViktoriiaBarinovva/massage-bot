# main.py

import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN
from database.db import init_db
from notifications import scheduler, schedule_all_notifications
from handlers.booking import router as booking_router
from handlers.client import router as client_router
from handlers.admin import router as admin_router

async def start_healthcheck_server():
    """
    Запускает минимальный HTTP-сервер на порту из $PORT,
    чтобы Render увидел слушающий порт и не убил контейнер.
    """
    port = int(os.environ.get("PORT", 8000))
    app = web.Application()
    async def ping(request):
        return web.Response(text="OK")
    app.add_routes([web.get("/", ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Healthcheck server started on port {port}")

async def main():
    # 1) Инициализируем базу
    await init_db()

    # 2) Стартуем HTTP-сервер для healthcheck
    await start_healthcheck_server()

    # 3) Создаём бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 4) Регистрируем команды и роутеры
    await bot.set_my_commands([BotCommand("start", "Главное меню")])
    dp.include_router(admin_router)
    dp.include_router(client_router)
    dp.include_router(booking_router)

    # 5) Планируем напоминания
    await schedule_all_notifications(bot)
    scheduler.start()

    print("🤖 Bot started, polling…")
    # 6) Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
