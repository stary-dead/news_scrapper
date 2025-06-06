FROM python:3.12-slim

WORKDIR /app

# Копируем только необходимые файлы
COPY requirements.txt .
COPY parser/ parser/
COPY telegram_bot/rabbitmq_utils.py telegram_bot/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем парсер
CMD ["python", "-m", "parser.parser_service"]
