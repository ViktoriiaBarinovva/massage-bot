# config.py

from dotenv import load_dotenv
import os

# Загружаем переменные окружения из .env
load_dotenv()

# Токен вашего бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Путь к файлу вашей SQLite БД
# В .env у вас указано DB_NAME, поэтому берём его и называем DB_PATH
DB_PATH = os.getenv("DB_NAME", "massage_bot.db")

# ID администраторов
# В .env у вас указано MASSAGE_THERAPIST_ID — если вам нужно несколько админов,
# можно указать через запятую, например "12345,67890"
_admins = os.getenv("MASSAGE_THERAPIST_ID", "")
ADMIN_IDS = [int(x) for x in _admins.split(",") if x.strip()]

# (Опционально) Лог уровня, если нужно
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
