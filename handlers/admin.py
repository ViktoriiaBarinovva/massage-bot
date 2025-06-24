# handlers/admin.py

import re
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters.command import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from services.storage import (
    get_all_appointments, confirm_payment,
    get_appointments_by_range, add_schedule_slot, remove_schedule_slot
)
from utils import parse_russian_datetime
from keyboards.client_kb import admin_menu

router = Router()


# FSM states
class AdminStates(StatesGroup):
    confirming = State()
    editing    = State()
    entering   = State()

class BulkStates(StatesGroup):
    choosing = State()
    entering = State()

class WeekAddStates(StatesGroup):
    entering = State()

class WeekRemoveStates(StatesGroup):
    entering = State()

class MonthAddStates(StatesGroup):
    entering = State()

class MonthRemoveStates(StatesGroup):
    entering = State()


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


# /start → show menu
@router.message(Command("start"))
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("👋 Админ-меню:", reply_markup=admin_menu())


# «⬅️ Назад» → clear state & menu
@router.message(F.text == "⬅️ Назад")
async def admin_go_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отмена. Главное меню:", reply_markup=admin_menu())


# Confirm payment
@router.message(F.text == "✅ Подтвердить оплату")
async def cmd_confirm(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return

    recs = await get_all_appointments()
    unpaid = [r for r in recs if r["payment_status"] == "не оплачено"]
    if not unpaid:
        return await message.answer("Нет неоплаченных записей.", reply_markup=admin_menu())

    await state.set_state(AdminStates.confirming)
    await state.update_data(records=unpaid)

    keyboard = [
        *[[KeyboardButton(text=f"{r['user_id']}|{r['date']} {r['time']}")] for r in unpaid],
        [KeyboardButton(text="⬅️ Назад")]
    ]
    kb = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await message.answer("Выберите запись для подтверждения оплаты:", reply_markup=kb)

@router.message(AdminStates.confirming)
async def on_confirm(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    try:
        uid_s, rest = message.text.split("|", 1)
        uid = int(uid_s)
        date, time = rest.split()
    except ValueError:
        return await message.answer("❌ Формат: user_id|DD МММ HH:MM")

    recs = (await state.get_data())["records"]
    match = next((r for r in recs if r["user_id"] == uid and r["date"] == date and r["time"] == time), None)
    if not match:
        return await message.answer("Запись не найдена.")

    await confirm_payment(uid, date, time)
    await state.clear()
    await message.answer("✅ Оплата подтверждена.", reply_markup=admin_menu())


# Single slot edit
@router.message(F.text == "🛠 Редактировать расписание")
async def cmd_edit(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return

    keyboard = [
        [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="➖ Удалить")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    kb = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await state.set_state(AdminStates.editing)
    await message.answer("Выберите действие:", reply_markup=kb)

@router.message(AdminStates.editing)
async def on_edit_choice(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    if message.text not in ("➕ Добавить", "➖ Удалить"):
        return await message.answer("Пожалуйста, выберите ➕ Добавить или ➖ Удалить.")
    await state.update_data(action=message.text)
    await state.set_state(AdminStates.entering)
    await message.answer(
        "Введите слот в формате `DD MMM HH:MM`, например `31 мая 14:00`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

@router.message(AdminStates.entering, ~F.text.startswith("/"))
async def on_enter_slot(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    try:
        dt = parse_russian_datetime(message.text)
    except ValueError:
        return await message.answer("❌ Пример: 31 мая 14:00")

    d_str = dt.strftime("%d %B")
    t_str = dt.strftime("%H:%M")
    action = (await state.get_data())["action"]
    if action == "➕ Добавить":
        await add_schedule_slot(d_str, t_str)
        resp = f"✅ Слот добавлен: {d_str} {t_str}"
    else:
        await remove_schedule_slot(d_str, t_str)
        resp = f"✅ Слот удалён: {d_str} {t_str}"

    await state.clear()
    await message.answer(resp, reply_markup=admin_menu())


# Bulk range edit
@router.message(F.text == "🔄 Групповое редактирование")
async def cmd_bulk(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return

    keyboard = [
        [KeyboardButton(text="➕ Добавить диапазон")],
        [KeyboardButton(text="➖ Удалить диапазон")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    kb = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await state.set_state(BulkStates.choosing)
    await message.answer("Массовое редактирование — выберите действие:", reply_markup=kb)

@router.message(BulkStates.choosing)
async def on_bulk_choice(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    if message.text not in ("➕ Добавить диапазон", "➖ Удалить диапазон"):
        return await message.answer("Пожалуйста, выберите одну из кнопок.")
    await state.update_data(bulk_action=message.text)
    await state.set_state(BulkStates.entering)
    await message.answer(
        "Введите диапазон в формате:\n`DD MMM — DD MMM HH:MM—HH:MM`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

@router.message(BulkStates.entering, ~F.text.startswith("/"))
async def on_bulk_enter(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    m = re.match(r"(\d{1,2} \w+)\s*[-–—]\s*(\d{1,2} \w+)\s+(\d{1,2}:\d{2})—(\d{1,2}:\d{2})", message.text)
    if not m:
        return await message.answer("❌ Неверный формат.")
    d1_s, d2_s, t1_s, t2_s = m.groups()
    d1 = parse_russian_datetime(f"{d1_s} 00:00")
    d2 = parse_russian_datetime(f"{d2_s} 00:00")
    t1_h, t1_m = map(int, t1_s.split(":"))
    t2_h, t2_m = map(int, t2_s.split(":"))
    if d2 < d1:
        return await message.answer("❌ Вторая дата раньше первой.")

    action = (await state.get_data())["bulk_action"]
    cnt, cur = 0, d1
    while cur.date() <= d2.date():
        h = t1_h
        while (h < t2_h) or (h == t2_h and t1_m < t2_m):
            ds = cur.strftime("%d %B")
            ts = f"{h:02d}:{t1_m:02d}"
            if action.startswith("➕"):
                await add_schedule_slot(ds, ts)
            else:
                await remove_schedule_slot(ds, ts)
            cnt += 1
            h += 1
        cur += timedelta(days=1)

    verb = "добавлено" if action.startswith("➕") else "удалено"
    await state.clear()
    await message.answer(f"✅ Диапазон обработан: {cnt} слотов {verb}.", reply_markup=admin_menu())


# Week add
@router.message(F.text == "➕ Добавить неделю")
async def start_week_add(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    await state.set_state(WeekAddStates.entering)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
    await message.answer(
        "Введите дату начала недели и время:\n`DD MMM HH:MM—HH:MM`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.message(WeekAddStates.entering, ~F.text.startswith("/"))
async def on_week_add(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    m = re.match(r"(\d{1,2} \w+)\s+(\d{1,2}:\d{2})—(\d{1,2}:\d{2})", message.text)
    if not m:
        return await message.answer("❌ Формат: `DD MMM HH:MM—HH:MM`")
    d1_s, t1_s, t2_s = m.groups()
    d1 = parse_russian_datetime(f"{d1_s} 00:00")
    t1_h, t1_m = map(int, t1_s.split(":"))
    t2_h, t2_m = map(int, t2_s.split(":"))
    start, end = d1.date(), d1.date() + timedelta(days=6)
    cnt, cur = 0, d1
    while cur.date() <= end:
        h = t1_h
        while (h < t2_h) or (h == t2_h and t1_m < t2_m):
            ds = cur.strftime("%d %B")
            ts = f"{h:02d}:{t1_m:02d}"
            await add_schedule_slot(ds, ts)
            cnt += 1
            h += 1
        cur += timedelta(days=1)
    await state.clear()
    await message.answer(
        f"✅ Добавлено {cnt} слотов на неделю {start.strftime('%d %B')}–{end.strftime('%d %B')}.",
        reply_markup=admin_menu()
    )


# Week remove
@router.message(F.text == "➖ Удалить неделю")
async def start_week_remove(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    await state.set_state(WeekRemoveStates.entering)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
    await message.answer(
        "Введите дату начала недели и время:\n`DD MMM HH:MM—HH:MM`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.message(WeekRemoveStates.entering, ~F.text.startswith("/"))
async def on_week_remove(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    m = re.match(r"(\d{1,2} \w+)\s+(\d{1,2}:\d{2})—(\d{1,2}:\d{2})", message.text)
    if not m:
        return await message.answer("❌ Формат: `DD MMM HH:MM—HH:MM`")
    d1_s, t1_s, t2_s = m.groups()
    d1 = parse_russian_datetime(f"{d1_s} 00:00")
    t1_h, t1_m = map(int, t1_s.split(":"))
    t2_h, t2_m = map(int, t2_s.split(":"))
    start, end = d1.date(), d1.date() + timedelta(days=6)
    cnt, cur = 0, d1
    while cur.date() <= end:
        h = t1_h
        while (h < t2_h) or (h == t2_h and t1_m < t2_m):
            ds = cur.strftime("%d %B")
            ts = f"{h:02d}:{t1_m:02d}"
            await remove_schedule_slot(ds, ts)
            cnt += 1
            h += 1
        cur += timedelta(days=1)
    await state.clear()
    await message.answer(
        f"✅ Удалено {cnt} слотов на неделю {start.strftime('%d %B')}–{end.strftime('%d %B')}.",
        reply_markup=admin_menu()
    )


# Month add
@router.message(F.text == "➕ Добавить месяц")
async def start_month_add(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    await state.set_state(MonthAddStates.entering)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
    await message.answer(
        "Введите дату начала месяца и время:\n`DD MMM HH:MM—HH:MM`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.message(MonthAddStates.entering, ~F.text.startswith("/"))
async def on_month_add(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    m = re.match(r"(\d{1,2} \w+)\s+(\d{1,2}:\d{2})—(\d{1,2}:\d{2})", message.text)
    if not m:
        return await message.answer("❌ Формат: `DD MMM HH:MM—HH:MM`")
    d1_s, t1_s, t2_s = m.groups()
    d1 = parse_russian_datetime(f"{d1_s} 00:00")
    t1_h, t1_m = map(int, t1_s.split(":"))
    t2_h, t2_m = map(int, t2_s.split(":"))
    start, end = d1.date(), d1.date() + timedelta(days=29)
    cnt, cur = 0, d1
    while cur.date() <= end:
        h = t1_h
        while (h < t2_h) or (h == t2_h and t1_m < t2_m):
            ds = cur.strftime("%d %B")
            ts = f"{h:02d}:{t1_m:02d}"
            await add_schedule_slot(ds, ts)
            cnt += 1
            h += 1
        cur += timedelta(days=1)
    await state.clear()
    await message.answer(
        f"✅ Добавлено {cnt} слотов на месяц {start.strftime('%d %B')}–{end.strftime('%d %B')}.",
        reply_markup=admin_menu()
    )


# Month remove
@router.message(F.text == "➖ Удалить месяц")
async def start_month_remove(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    await state.set_state(MonthRemoveStates.entering)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
    await message.answer(
        "Введите дату начала месяца и время:\n`DD MMM HH:MM—HH:MM`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.message(MonthRemoveStates.entering, ~F.text.startswith("/"))
async def on_month_remove(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await admin_go_back(message, state)
    m = re.match(r"(\d{1,2} \w+)\s+(\d{1,2}:\d{2})—(\d{1,2}:\d{2})", message.text)
    if not m:
        return await message.answer("❌ Формат: `DD MMM HH:MM—HH:MM`")
    d1_s, t1_s, t2_s = m.groups()
    d1 = parse_russian_datetime(f"{d1_s} 00:00")
    t1_h, t1_m = map(int, t1_s.split(":"))
    t2_h, t2_m = map(int, t2_s.split(":"))
    start, end = d1.date(), d1.date() + timedelta(days=29)
    cnt, cur = 0, d1
    while cur.date() <= end:
        h = t1_h
        while (h < t2_h) or (h == t2_h and t1_m < t2_m):
            ds = cur.strftime("%d %B")
            ts = f"{h:02d}:{t1_m:02d}"
            await remove_schedule_slot(ds, ts)
            cnt += 1
            h += 1
        cur += timedelta(days=1)
    await state.clear()
    await message.answer(
        f"✅ Удалено {cnt} слотов на месяц {start.strftime('%d %B')}–{end.strftime('%d %B')}.",
        reply_markup=admin_menu()
    )


# View appointments
@router.message(F.text == "📅 Сегодня")
async def view_today(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    today = datetime.now().date().strftime("%d %B")
    recs = await get_appointments_by_range(today, today)
    text = "\n".join(f"{r['date']} {r['time']} — {r['service']} (u{r['user_id']})" for r in recs) or "Пусто"
    await message.answer(f"📅 Сегодня:\n{text}", reply_markup=admin_menu())

@router.message(F.text == "🗓 Неделя")
async def view_week(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    start = datetime.now().date()
    end   = start + timedelta(days=7)
    sd, ed = start.strftime("%d %B"), end.strftime("%d %B")
    recs = await get_appointments_by_range(sd, ed)
    text = "\n".join(f"{r['date']} {r['time']} — {r['service']} (u{r['user_id']})" for r in recs) or "Пусто"
    await message.answer(f"🗓 Неделя ({sd}–{ed}):\n{text}", reply_markup=admin_menu())

@router.message(F.text == "🗓 Месяц")
async def view_month(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    start = datetime.now().date()
    end   = start + timedelta(days=30)
    sd, ed = start.strftime("%d %B"), end.strftime("%d %B")
    recs = await get_appointments_by_range(sd, ed)
    text = "\n".join(f"{r['date']} {r['time']} — {r['service']} (u{r['user_id']})" for r in recs) or "Пусто"
    await message.answer(f"🗓 Месяц ({sd}–{ed}):\n{text}", reply_markup=admin_menu())

