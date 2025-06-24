# keyboards/client_kb.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="🗓 Мои записи")],
            [KeyboardButton(text="❌ Отменить запись")],
            [KeyboardButton(text="💰 Прайс-лист"), KeyboardButton(text="📞 Контакты")],
        ],
        resize_keyboard=True
    )

def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить оплату")],
            [KeyboardButton(text="🛠 Редактировать расписание"), KeyboardButton(text="🔄 Групповое редактирование")],
            [KeyboardButton(text="➕ Добавить неделю"), KeyboardButton(text="➖ Удалить неделю")],
            [KeyboardButton(text="➕ Добавить месяц"), KeyboardButton(text="➖ Удалить месяц")],
            [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="🗓 Неделя"), KeyboardButton(text="🗓 Месяц")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True
    )
