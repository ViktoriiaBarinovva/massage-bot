import aiosqlite
from config import DB_PATH
from datetime import date, timedelta

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            full_name TEXT
        )""")

        # Таблица записей клиентов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service TEXT,
            date TEXT,
            time TEXT,
            status TEXT,
            payment_status TEXT
        )""")

        # Таблица расписания слотов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            is_available INTEGER DEFAULT 1
        )""")

        # Таблица уведомлений
        await db.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            type TEXT
        )""")

        # Наполнение schedule: только вторник, четверг, суббота с 12:00 до 19:00
        today = date.today()
        end_of_year = date(today.year, 12, 31)
        current = today
        # weekday(): Monday=0, Tuesday=1, Thursday=3, Saturday=5
        allowed_weekdays = {1, 3, 5}
        while current <= end_of_year:
            if current.weekday() in allowed_weekdays:
                d_str = current.strftime("%d %B")
                for hour in range(12, 20):  # 12..19 включительно
                    time_str = f"{hour:02d}:00"
                    await db.execute(
                        "INSERT OR IGNORE INTO schedule (date, time) VALUES (?, ?)",
                        (d_str, time_str)
                    )
            current += timedelta(days=1)

        await db.commit()
