# main.py

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from notifications import schedule_all_notifications
from handlers.booking import router as booking_router
from handlers.client import router as client_router
from handlers.admin import router as admin_router

async def main():
    # 1. Инициализация базы
    await init_db()

    # 2. Создание бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Установка команд в меню
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="admin", description="Админ-меню")
    ])

    # 4. Подключение роутеров
    dp.include_router(admin_router)
    dp.include_router(client_router)
    dp.include_router(booking_router)

    # 5. Планирование уведомлений (scheduler стартует внутри)
    await schedule_all_notifications(bot)

    print("Бот запущен")
    try:
        # 6. Запуск polling
        await dp.start_polling(bot)
    finally:
        # 7. Корректное закрытие сессии aiohttp
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
