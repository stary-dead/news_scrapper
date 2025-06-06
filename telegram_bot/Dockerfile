FROM python:3.12-slim

WORKDIR /app

# Копируем только необходимые файлы
COPY requirements.txt .
COPY telegram_bot/ telegram_bot/
COPY parser/categories.py parser/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем бота
CMD ["python", "-m", "telegram_bot.bot"]
