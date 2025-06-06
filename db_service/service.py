"""
Сервис для обработки статей и отправки их в Telegram
"""
import asyncio
import logging
from typing import Dict
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from telegram_bot.rabbitmq_utils import RabbitMQClient
from .database import DatabaseService

# Get environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "news_db")

# Constants
DB_CONNECTION = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
ARTICLES_QUEUE = "new_articles"              # Очередь для новых статей
PARSED_ARTICLES_QUEUE = "parsed_articles"    # Очередь для обработанных статей
TELEGRAM_CHANNEL_ID = -1002745773579        # ID канала для отправки новостей
CHECK_INTERVAL = 10                         # Интервал проверки новых статей (секунд)
PUBLISH_DELAY = 2                          # Задержка между публикациями

class ArticleProcessor:
    def __init__(self):
        self.db = DatabaseService(DB_CONNECTION)
        self.rabbitmq = RabbitMQClient()
        
    async def process_new_article(self, message: Dict) -> None:
        """
        Обработка новой статьи
        
        Args:
            message (Dict): Сообщение с данными статьи
        """
        article = message.get('article')
        category_name = message.get('category_name')
        
        if not article or not category_name:
            return
            
        # Пытаемся сохранить статью в базу
        saved = await self.db.save_article(article, category_name)
        
        if saved:
            logging.info(f"Successfully saved article: {article.get('title')}")
        else:
            logging.info(f"Article already exists: {article.get('title')}")
            
    async def process_articles_queue(self) -> None:
        """Обработка очереди с новыми статьями"""
        async def callback(message):
            await self.process_new_article(message)
            
        await self.rabbitmq.consume_messages(ARTICLES_QUEUE, callback)
        
    async def check_and_publish_articles(self) -> None:
        """Проверка и публикация необработанных статей"""
        while True:
            try:
                # Получаем непубликованные статьи
                articles = await self.db.get_unprocessed_articles(limit=10)
                
                for article in articles:
                    # Формируем сообщение для отправки                      
                    message = {
                        "channel_id": TELEGRAM_CHANNEL_ID,
                        "article": article,  # Передаем всю статью целиком
                        "category_name": article['category_name']
                    }
                    
                    # Публикуем в очередь для бота
                    await self.rabbitmq.publish_message(PARSED_ARTICLES_QUEUE, message)
                    
                    # Отмечаем как обработанную
                    await self.db.mark_article_as_processed(article['id'])
                    
                    # Добавляем задержку между публикациями
                    await asyncio.sleep(PUBLISH_DELAY)
                    
            except Exception as e:
                logging.error(f"Error processing articles: {e}")
                
            await asyncio.sleep(CHECK_INTERVAL)
            
    async def start(self):
        """Запуск сервиса"""
        try:
            # Инициализируем базу данных
            self.db.init_db()
            
            # Подключаемся к RabbitMQ
            await self.rabbitmq.connect()
            
            # Объявляем очереди
            await self.rabbitmq.declare_queue(ARTICLES_QUEUE)
            await self.rabbitmq.declare_queue(PARSED_ARTICLES_QUEUE)
            
            # Запускаем обработчики
            await asyncio.gather(
                self.process_articles_queue(),
                self.check_and_publish_articles()
            )
            
        except Exception as e:
            logging.error(f"Error starting service: {e}")
            raise

async def main():
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Запускаем сервис
    processor = ArticleProcessor()
    await processor.start()

if __name__ == "__main__":
    asyncio.run(main())
