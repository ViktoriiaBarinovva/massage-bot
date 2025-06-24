import logging
from datetime import datetime, timedelta, date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from utils import parse_russian_datetime
from services.storage import get_all_appointments, get_appointments_by_range
from config import ADMIN_IDS

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def schedule_all_notifications(bot: Bot):
    """
    Планирует:
      – персональные напоминания клиентам и админам за день и за час до сеанса
      – ежедневную сводку администратору о записях на завтра
    """
    # очищаем старые задачи
    scheduler.remove_all_jobs()

    now = datetime.now()
    recs = await get_all_appointments()

    for r in recs:
        # фильтруем отменённые и неоплаченные
        if r["status"] == "отменена" or r.get("payment_status") != "оплачено":
            continue

        # парсим дату+время
        dt = parse_russian_datetime(f"{r['date']} {r['time']}")

        # напоминание за день в 09:00
        day_before = (dt - timedelta(days=1)).replace(hour=9, minute=0, second=0)
        if day_before > now:
            scheduler.add_job(
                send_reminder,
                trigger=DateTrigger(run_date=day_before),
                args=[bot, r["user_id"], dt, "за день"],
                id=f"reminder_day_{r['id']}",
                replace_existing=True,
            )
            for admin_id in ADMIN_IDS:
                scheduler.add_job(
                    send_admin_notification,
                    trigger=DateTrigger(run_date=day_before),
                    args=[bot, admin_id, r, dt, "за день"],
                    id=f"admin_day_{r['id']}_{admin_id}",
                    replace_existing=True,
                )

        # напоминание за час до
        hour_before = dt - timedelta(hours=1)
        if hour_before > now:
            scheduler.add_job(
                send_reminder,
                trigger=DateTrigger(run_date=hour_before),
                args=[bot, r["user_id"], dt, "за час"],
                id=f"reminder_hour_{r['id']}",
                replace_existing=True,
            )
            for admin_id in ADMIN_IDS:
                scheduler.add_job(
                    send_admin_notification,
                    trigger=DateTrigger(run_date=hour_before),
                    args=[bot, admin_id, r, dt, "за час"],
                    id=f"admin_hour_{r['id']}_{admin_id}",
                    replace_existing=True,
                )

    # ежедневная сводка: каждый день в 18:00
    scheduler.add_job(
        send_daily_summary,
        trigger=CronTrigger(hour=18, minute=0),
        args=[bot],
        id="daily_summary",
        replace_existing=True,
    )

    # запуск планировщика
    if not scheduler.running:
        scheduler.start()

async def send_reminder(bot: Bot, user_id: int, dt: datetime, when: str):
    text = f"📅 Напоминание: ваша запись {dt.strftime('%d %B %Y в %H:%M')} — {when}!"
    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        logger.error(f"Не удалось отправить напоминание ({when}) user_id={user_id}: {e}")

async def send_admin_notification(bot: Bot, admin_id: int, appointment: dict, dt: datetime, when: str):
    text = (
        f"⚙️ Напоминание админу ({when}):\n"
        f"Пользователь u{appointment['user_id']} — {appointment['service']}\n"
        f"Дата: {dt.strftime('%d %B %Y в %H:%M')}"
    )
    try:
        await bot.send_message(admin_id, text)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу={admin_id}: {e}")

async def send_daily_summary(bot: Bot):
    """
    Ежедневная рассылка администратору списка всех записей на завтра.
    """
    tomorrow = date.today() + timedelta(days=1)
    start = tomorrow.strftime('%d %B')
    end = start  # только одна дата
    recs = await get_appointments_by_range(start, end)

    if not recs:
        text = f"📋 Рассылка: нет записей на {start}."
    else:
        lines = [f"{r['time']} — {r['service']} (u{r['user_id']})" for r in recs]
        text = "📋 Записи на завтра (" + start + "):\n" + "\n".join(lines)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logger.error(f"Не удалось отправить сводку админу={admin_id}: {e}")
