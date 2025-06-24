from aiogram.types import Message
from keyboards.client_kb import main_menu

async def send_with_main_menu(message: Message, text: str):
    await message.answer(text, reply_markup=main_menu())
