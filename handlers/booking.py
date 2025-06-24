# handlers/booking.py

from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from utils import parse_russian_datetime, send_with_main_menu
from services.storage import is_slot_taken, save_appointment

router = Router()

class BookingStates(StatesGroup):
    choosing_gender = State()
    choosing_service = State()
    choosing_datetime = State()

# Услуги для разных полов (можно скорректировать списки)
FEMALE_SERVICES = [
    "Классический массаж — 60 мин — 2 500₽",
    "Массаж спины + (зона ШВЗ) — 40 мин — 2 000₽",
    "Антицеллюлитный массаж — 60 мин — 2 000₽",
]
MALE_SERVICES = [
    "Классический массаж — 60 мин — 2 500₽",
    "Массаж спины + (зона ШВЗ) — 40 мин — 2 500₽",
]

@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Девушка"), KeyboardButton(text="Мужчина")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите ваш пол:", reply_markup=kb)
    await state.set_state(BookingStates.choosing_gender)

@router.message(BookingStates.choosing_gender, F.text.in_(["Девушка", "Мужчина"]))
async def choose_gender(message: Message, state: FSMContext):
    gender = message.text
    await state.update_data(gender=gender)

    # Выбираем прайс-лист по полу
    services = FEMALE_SERVICES if gender == "Девушка" else MALE_SERVICES
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=s)] for s in services] + [[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )
    await message.answer("Выберите услугу:", reply_markup=kb)
    await state.set_state(BookingStates.choosing_service)

@router.message(BookingStates.choosing_gender)
async def choose_gender_invalid(message: Message):
    await message.answer("❌ Пожалуйста, выберите «Девушка» или «Мужчина» кнопкой.")

@router.message(BookingStates.choosing_service, StateFilter(F.text.in_(FEMALE_SERVICES + MALE_SERVICES)))
async def choose_service(message: Message, state: FSMContext):
    await state.update_data(service=message.text)
    await message.answer(
        "Введите дату и время (пример: 31 мая 14:00):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(BookingStates.choosing_datetime)

@router.message(BookingStates.choosing_service)
async def choose_service_invalid(message: Message):
    await message.answer("❌ Пожалуйста, выберите услугу кнопкой из списка.")

@router.message(BookingStates.choosing_datetime)
async def choose_datetime(message: Message, state: FSMContext):
    text = message.text
    try:
        dt = parse_russian_datetime(text)
    except Exception:
        return await message.answer("❌ Неверный формат. Пример: 31 мая 14:00")

    if dt < datetime.now():
        return await message.answer("❌ Выбрана прошедшая дата.")

    date_str = dt.strftime("%d %B")
    time_str = dt.strftime("%H:%M")

    if await is_slot_taken(date_str, time_str):
        return await message.answer("❌ Слот занят, выберите другое время.")

    data = await state.get_data()
    appt_id = await save_appointment({
        "user_id": message.from_user.id,
        "service": data["service"],
        "date": date_str,
        "time": time_str
    })

    payment_info = (
        "🔔 Для подтверждения брони переведите 500 ₽ на номер +7 XXX XXX XX XX.\n"
        "Предоплата не возвращается при отмене.\n\n"
        "После оплаты администратор подтвердит вашу запись."
    )

    await send_with_main_menu(
        message,
        f"✅ Ваша заявка принята!\n"
        f"<b>Услуга:</b> {data['service']}\n"
        f"<b>Дата:</b> {date_str}\n"
        f"<b>Время:</b> {time_str}\n\n"
        f"{payment_info}"
    )
    await state.clear()

@router.message(BookingStates.choosing_datetime)
async def choose_datetime_invalid(message: Message):
    await message.answer("❌ Неверный ввод. Введите дату и время, например: 31 мая 14:00")

# Общий хэндлер «Назад» для всех состояний BookingStates
@router.message(F.text == "⬅️ Назад", StateFilter(BookingStates))
async def booking_go_back(message: Message, state: FSMContext):
    await state.clear()
    # Возвращаем пользователя в главное меню
    from keyboards.client_kb import client_menu
    await message.answer("Отмена. Главное меню:", reply_markup=client_menu())
