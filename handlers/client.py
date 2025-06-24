# handlers/client.py

from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from config import ADMIN_IDS
from utils import parse_russian_datetime, send_with_main_menu
from services.storage import (
    get_user_appointments,
    cancel_appointment,
    update_appointment,
    is_slot_taken,
    save_appointment,
)
from keyboards.client_kb import client_menu, admin_menu

router = Router()

class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_datetime = State()

class CancelStates(StatesGroup):
    choosing = State()

class RescheduleStates(StatesGroup):
    choosing = State()
    new_time = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# возврат «Назад»
@router.message(F.text == "⬅️ Назад")
async def go_back(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("Отмена. Главное меню:", reply_markup=admin_menu())
    else:
        await message.answer("Отмена. Главное меню:", reply_markup=client_menu())

# старт
@router.message(Command("start"))
async def on_start(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer("Привет, администратор!", reply_markup=admin_menu())
    else:
        await message.answer(f"Привет, {message.from_user.full_name}!", reply_markup=client_menu())

# запись
SERVICES = [
    "Классический массаж — 60 мин — 2 500₽",
    "Спина + ШВЗ — 40 мин — 2 000₽",
    "Антицеллюлитный массаж — 60 мин — 2 000₽",
]

@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in SERVICES:
        kb.add(KeyboardButton(text=s))
    kb.add(KeyboardButton(text="⬅️ Назад"))
    await message.answer("Выберите услугу:", reply_markup=kb)
    await state.set_state(BookingStates.choosing_service)

@router.message(BookingStates.choosing_service)
async def choose_service(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await go_back(message, state)
    service = message.text
    if service not in SERVICES:
        return await message.answer("Пожалуйста, выберите услугу кнопкой.")
    await state.update_data(service=service)
    await message.answer("Введите дату и время (например: 31 мая 14:00):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(BookingStates.choosing_datetime)

@router.message(BookingStates.choosing_datetime)
async def choose_datetime(message: Message, state: FSMContext):
    text = message.text
    try:
        dt = parse_russian_datetime(text)
    except:
        return await message.answer("❌ Неверный формат. Пример: 31 мая 14:00")
    if dt < datetime.now():
        return await message.answer("❌ Вы выбрали прошедшую дату.")
    date_str = dt.strftime("%d %B")
    time_str = dt.strftime("%H:%M")
    if await is_slot_taken(date_str, time_str):
        return await message.answer("❌ Слот занят. Выберите другое время.")
    data = await state.get_data()
    await save_appointment({
        "user_id": message.from_user.id,
        "service": data["service"],
        "date": date_str,
        "time": time_str
    })
    await send_with_main_menu(
        message,
        f"✅ Вы записаны!\n\n"
        f"<b>Услуга:</b> {data['service']}\n"
        f"<b>Дата:</b> {date_str}\n"
        f"<b>Время:</b> {time_str}"
    )
    await state.clear()

# мои записи
@router.message(F.text == "🗓 Мои записи")
async def my_records(message: Message):
    recs = await get_user_appointments(message.from_user.id)
    now = datetime.now()
    out = []
    for r in recs:
        try:
            dt = parse_russian_datetime(f"{r['date']} {r['time']}")
            if r["status"] != "отменена" and dt > now:
                out.append(r)
        except:
            pass
    if not out:
        return await message.answer("Нет актуальных записей.")
    text = "🗓 Ваши записи:\n\n"
    for i, r in enumerate(out,1):
        text += (f"{i}) {r['date']} {r['time']}\n"
                 f"   {r['service']} | {r['status']} | {r['payment_status']}\n\n")
    await message.answer(text)

# отмена
@router.message(F.text == "❌ Отменить запись")
async def cancel_start(message: Message, state: FSMContext):
    recs = await get_user_appointments(message.from_user.id)
    now = datetime.now()
    valid = [r for r in recs if r["status"]!="отменена" and parse_russian_datetime(f"{r['date']} {r['time']}")-now>timedelta(hours=24)]
    if not valid:
        return await message.answer("Нет записей для отмены.")
    await state.set_state(CancelStates.choosing)
    await state.update_data(records=valid)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for r in valid:
        kb.add(KeyboardButton(text=f"{r['date']} {r['time']}"))
    kb.add(KeyboardButton(text="⬅️ Назад"))
    await message.answer("Выберите запись:", reply_markup=kb)

@router.message(CancelStates.choosing)
async def cancel_confirm(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await go_back(message, state)
    recs = (await state.get_data())["records"]
    match = next((r for r in recs if f"{r['date']} {r['time']}"==message.text), None)
    if not match:
        return await message.answer("Неверный выбор.")
    await cancel_appointment(message.from_user.id, match["date"], match["time"])
    await message.answer("✅ Отменено.", reply_markup=client_menu())
    await state.clear()

# перенос
@router.message(F.text == "🔁 Перенести запись")
async def resch_start(message: Message, state: FSMContext):
    recs = await get_user_appointments(message.from_user.id)
    now = datetime.now()
    valid = [r for r in recs if r["status"]!="отменена" and parse_russian_datetime(f"{r['date']} {r['time']}")-now>timedelta(hours=24)]
    if not valid:
        return await message.answer("Нет записей для переноса.")
    await state.set_state(RescheduleStates.choosing)
    await state.update_data(records=valid)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for r in valid:
        kb.add(KeyboardButton(text=f"{r['date']} {r['time']}"))
    kb.add(KeyboardButton(text="⬅️ Назад"))
    await message.answer("Выберите старую запись:", reply_markup=kb)

@router.message(RescheduleStates.choosing)
async def resch_choose_old(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await go_back(message, state)
    recs = (await state.get_data())["records"]
    match = next((r for r in recs if f"{r['date']} {r['time']}"==message.text), None)
    if not match:
        return await message.answer("Неверный выбор.")
    await state.update_data(old=match)
    await state.set_state(RescheduleStates.new_time)
    await message.answer("Введите новую дату и время:", reply_markup=ReplyKeyboardRemove())
    # показать «Назад»
    await message.answer("Если хотите отменить — нажмите «⬅️ Назад»", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("⬅️ Назад")]], resize_keyboard=True))

@router.message(RescheduleStates.new_time)
async def resch_confirm(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        return await go_back(message, state)
    try:
        dt = parse_russian_datetime(message.text)
    except:
        return await message.answer("❌ Неверный формат.")
    if dt < datetime.now() + timedelta(hours=24):
        return await message.answer("❌ Менее чем за 24 ч.")
    old = (await state.get_data())["old"]
    new_d, new_t = dt.strftime("%d %B"), dt.strftime("%H:%M")
    await update_appointment(message.from_user.id, old["date"], old["time"], new_d, new_t)
    await message.answer(f"✅ Перенесено на {new_d} {new_t}", reply_markup=client_menu())
    await state.clear()

# прайс и контакты
@router.message(F.text == "💰 Прайс-лист")
async def price_list(message: Message):
    await message.answer(
        "💰 Прайс-лист:\n\n"
        "— Классический — 60 мин — 2 500₽\n"
        "— Спина+ШВЗ — 40 мин — 2 000₽\n"
        "— Антицеллюлитный — 60 мин — 2 000₽"
    )

@router.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    await message.answer(
        "📞 Контакты:\n"
        "+7 939 754 46 24\n"
        "@v_muzhikova\n"
        "г. Самара, ул. Революционная 70/2, 231"
    )
