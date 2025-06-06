"""Main bot module for channel news posting"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from telegram_bot.config import BotConfig
import sys
import os
from datetime import datetime
from telegram_bot.rabbitmq_utils import RabbitMQClient

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from parser.categories import CategoryStructure

# Initialize bot and dispatcher
bot = Bot(token=BotConfig().token)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Initialize RabbitMQ client
rabbitmq_client = RabbitMQClient()

# Constants
PARSED_ARTICLES_QUEUE = "parsed_articles"      # Очередь для обработанных статей
TELEGRAM_CHANNEL_ID = -1002745773579          # ID канала для отправки новостей
MESSAGE_DELAY = 5                             # Задержка между отправкой сообщений (секунды)
MAX_RETRIES = 3                              # Максимальное количество попыток отправки сообщения

# Семафор для ограничения параллельной обработки сообщений
message_semaphore = asyncio.Semaphore(2)  # Максимум 2 сообщения одновременно

async def send_telegram_message(chat_id: int, message_text: str, photo_url: str = None) -> bool:
    """
    Отправка сообщения в Telegram с повторными попытками
    
    Args:
        chat_id (int): ID чата/канала
        message_text (str): Текст сообщения
        photo_url (str, optional): URL изображения
        
    Returns:
        bool: True если сообщение отправлено успешно
    """
    for attempt in range(MAX_RETRIES):
        try:
            if photo_url:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_url,
                    caption=message_text,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            return True
            
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            continue
            
    return False

async def process_article_message(message: dict) -> None:
    """
    Обработчик сообщений из очереди RabbitMQ с контролем скорости
    
    Args:
        message (dict): Сообщение с данными статьи
    """
    async with message_semaphore:  # Контролируем количество параллельных отправок
        try:
            article = message.get("article")
            category_name = message.get("category_name")
            
            if not article:
                logging.error("Отсутствуют данные статьи в сообщении")
                return

            # Подготовка текста сообщения
            message_text = (
                f"📰 *{article['title']}*\n\n"
                f"📁 {category_name}\n"
                f"🔍 {article.get('subtitle', '')}\n\n"
                f"📅 {article.get('publication_date', 'Data nie podana')}\n"
                f"✍️ {article.get('author', 'Autor nie podany')}\n\n"
                f"🔗 [Czytaj więcej]({article['url']})"
            )

            # Отправка сообщения с повторными попытками
            success = await send_telegram_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                message_text=message_text,
                photo_url=article.get('image_url')
            )

            if success:
                # Добавляем задержку между сообщениями для равномерного потока
                await asyncio.sleep(MESSAGE_DELAY)
            else:
                logging.error("Failed to send message after all retries")
                
        except Exception as e:
            logging.error(f"Ошибка обработки статьи: {e}")

async def start_rabbitmq():
    """
    Инициализация и настройка подключения к RabbitMQ
    """
    try:
        await rabbitmq_client.connect()
        await rabbitmq_client.declare_queue(PARSED_ARTICLES_QUEUE)
        await rabbitmq_client.consume_messages(PARSED_ARTICLES_QUEUE, process_article_message)
        logging.info("RabbitMQ успешно инициализирован")
    except Exception as e:
        logging.error(f"Ошибка инициализации RabbitMQ: {e}")
        raise

async def main():
    """Main function"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Инициализируем RabbitMQ
    await start_rabbitmq()
    
    try:
        # Отправляем приветственное сообщение в канал при запуске
        await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text="🤖 Bot został uruchomiony i rozpoczyna monitoring wiadomości.\n"
                 "Nowe artykuły będą automatycznie publikowane w tym kanale.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки приветственного сообщения: {e}")
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
