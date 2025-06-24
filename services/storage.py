# services/storage.py

import aiosqlite
from config import DB_PATH

async def save_appointment(data: dict) -> int:
    """
    Сохраняет новую запись с дефолтными статусами:
      status = 'запланирована'
      payment_status = 'не оплачено'
    Возвращает ID созданной записи.
    data = {
      'user_id': int,
      'service': str,
      'date': str,
      'time': str
    }
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO appointments
                (user_id, service, date, time, status, payment_status)
            VALUES (?, ?, ?, ?, 'запланирована', 'не оплачено')
            """,
            (data["user_id"], data["service"], data["date"], data["time"])
        )
        await db.commit()
        return cursor.lastrowid

async def is_slot_taken(date: str, time: str) -> bool:
    """
    Проверяет, занят ли слот (любая не отменённая запись).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT COUNT(*) FROM appointments
            WHERE date = ? AND time = ? AND status != 'отменена'
            """,
            (date, time)
        ) as cur:
            cnt, = await cur.fetchone()
            return cnt > 0

async def get_user_appointments(user_id: int) -> list[dict]:
    """
    Возвращает все записи пользователя (любые статусы, для клиента фильтрация по дате в хэндлерах).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT id, date, time, service, status, payment_status
            FROM appointments
            WHERE user_id = ?
            ORDER BY date, time
            """,
            (user_id,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def cancel_appointment(user_id: int, date: str, time: str):
    """
    Помечает запись отменённой.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE appointments
            SET status = 'отменена'
            WHERE user_id = ? AND date = ? AND time = ? AND status != 'отменена'
            """,
            (user_id, date, time)
        )
        await db.commit()

async def update_appointment(
    user_id: int,
    old_date: str, old_time: str,
    new_date: str, new_time: str
):
    """
    Переносит запись на новую дату/время.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE appointments
            SET date = ?, time = ?
            WHERE user_id = ? AND date = ? AND time = ? AND status != 'отменена'
            """,
            (new_date, new_time, user_id, old_date, old_time)
        )
        await db.commit()

async def confirm_payment(user_id: int, date: str, time: str):
    """
    Админ вызывает для подтверждения оплаты:
      payment_status = 'оплачено'
      status = 'подтверждена'
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE appointments
            SET payment_status = 'оплачено', status = 'подтверждена'
            WHERE user_id = ? AND date = ? AND time = ? AND status != 'отменена'
            """,
            (user_id, date, time)
        )
        await db.commit()

async def get_all_appointments() -> list[dict]:
    """
    Возвращает все ненулевые (не отменённые) записи для админа.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT id, user_id, service, date, time, status, payment_status
            FROM appointments
            WHERE status != 'отменена'
            ORDER BY date, time
            """
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def get_appointments_by_range(start_date: str, end_date: str) -> list[dict]:
    """
    Возвращает ненулевые записи между start_date и end_date (включительно).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT id, user_id, service, date, time, status, payment_status
            FROM appointments
            WHERE status != 'отменена'
              AND date BETWEEN ? AND ?
            ORDER BY date, time
            """,
            (start_date, end_date)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

async def add_schedule_slot(date: str, time: str):
    """
    Админ добавляет слот в расписание.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO schedule (date, time) VALUES (?, ?)",
            (date, time)
        )
        await db.commit()

async def remove_schedule_slot(date: str, time: str):
    """
    Админ удаляет слот из расписания.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM schedule WHERE date = ? AND time = ?",
            (date, time)
        )
        await db.commit()
