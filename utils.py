from datetime import datetime
from aiogram.types import Message

# Маппинг русских названий месяцев
_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

def parse_russian_datetime(text: str) -> datetime:
    """
    Принимает "31 мая 14:00" или "31 мая 2025 14:00".
    Возвращает datetime.
    """
    parts = text.strip().split()
    if len(parts) == 3:
        day, month_str, time_str = parts
        year = datetime.now().year
    elif len(parts) == 4:
        day, month_str, year, time_str = parts
        year = int(year)
    else:
        raise ValueError("Ожидается формат '31 мая 14:00'")

    month = _MONTHS.get(month_str.lower())
    if not month:
        raise ValueError(f"Непонятный месяц '{month_str}'")

    hour, minute = map(int, time_str.split(":"))
    return datetime(int(year), month, int(day), hour, minute)

async def send_with_main_menu(message: Message, text: str):
    from keyboards.client_kb import main_menu
    await message.answer(text, reply_markup=main_menu())
