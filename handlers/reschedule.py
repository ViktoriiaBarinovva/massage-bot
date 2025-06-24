from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.storage import get_user_appointments, is_slot_taken, update_appointment
from keyboards.client_kb import client_menu, admin_menu

from datetime import datetime, timedelta

router = Router()

available_dates = ["27 мая", "29 мая", "31 мая"]
available_times = ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]

class RescheduleStates(StatesGroup):
    choosing_record = State()
    choosing_new_time = State()


@router.message(F.text == "🔄 Перенести запись")
async def start_reschedule(message: Message, state: FSMContext):
    user_id = message.from_user.id
    records = await get_user_appointments(user_id)
    records = [dict(r) for r in records]

    active = [r for r in records if r["status"] != "отменена"]
    if not active:
        await message.answer("У вас нет активных записей для переноса.", reply_markup=main_menu())
        return

    await state.set_state(RescheduleStates.choosing_record)
    await state.update_data(records=active)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(f"{r['date']} {r['time']}")] for r in active],
        resize_keyboard=True
    )
    await message.answer("Выберите запись, которую хотите перенести:", reply_markup=kb)


@router.message(RescheduleStates.choosing_record)
async def choose_new_slot(message: Message, state: FSMContext):
    chosen = message.text
    data = await state.get_data()
    records = data["records"]

    match = next((r for r in records if f"{r['date']} {r['time']}" == chosen), None)
    if not match:
        await message.answer("Запись не найдена.")
        await state.clear()
        return

    # Проверка: минимум за 1 день
    try:
        dt = datetime.strptime(f"{match['date']} {match['time']}", "%d %B %H:%M")
        now = datetime.now()
        if dt - timedelta(days=1) <= now:
            await message.answer("Перенос возможен минимум за 1 день до записи.", reply_markup=main_menu())
            await state.clear()
            return
    except Exception:
        await message.answer("Ошибка при проверке даты.", reply_markup=main_menu())
        await state.clear()
        return

    await state.update_data(old_date=match["date"], old_time=match["time"])
    await state.set_state(RescheduleStates.choosing_new_time)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(f"{d} {t}")] for d in available_dates for t in available_times],
        resize_keyboard=True
    )
    await message.answer("Выберите новую дату и время:", reply_markup=kb)


@router.message(RescheduleStates.choosing_new_time)
async def save_reschedule(message: Message, state: FSMContext):
    try:
        new_date, new_time = message.text.split(" ")
    except ValueError:
        await message.answer("Неверный формат. Пожалуйста, выберите из кнопок.")
        return

    data = await state.get_data()

    if await is_slot_taken(new_date, new_time):
        await message.answer("Это время уже занято. Выберите другое.")
        return

    await update_appointment(
        user_id=message.from_user.id,
        old_date=data["old_date"],
        old_time=data["old_time"],
        new_date=new_date,
        new_time=new_time
    )

    await message.answer(
        f"✅ Ваша запись перенесена на {new_date} в {new_time}.", reply_markup=main_menu()
    )
    await state.clear()
