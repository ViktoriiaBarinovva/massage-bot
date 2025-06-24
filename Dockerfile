
FROM python:3.12-slim

# 2. Рабочая директория
WORKDIR /app

# 3. Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Копируем весь код
COPY main.py config.py utils.py notifications.py ./
COPY handlers/    ./handlers
COPY services/    ./services
COPY database/    ./database
COPY keyboards/   ./keyboards

# 5. Папка для бэкапов
RUN mkdir -p /app/backups

# 6. Открываем порт для healthcheck
EXPOSE 8000

# 7. Запуск бота
CMD ["python", "main.py"]
