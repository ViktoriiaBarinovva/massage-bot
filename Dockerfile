# 1. Берём официальный образ Python 3.12
FROM python:3.12-slim

# 2. Устанавливаем рабочую директорию
WORKDIR /app

# 3. Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Копируем остальной код
COPY main.py config.py utils.py notifications.py ./
COPY handlers/    ./handlers
COPY services/    ./services
COPY database/    ./database
COPY keyboards/   ./keyboards

# 5. Создаём папку для бэкапов (если нужно)
RUN mkdir -p /app/backups

# 6. Запускаем бота
CMD ["python", "main.py"]
