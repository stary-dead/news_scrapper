"""
Сервис парсера для автоматического парсинга и отправки новостей в канал
"""
import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os
from typing import List, Tuple, Dict
from collections import defaultdict

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from telegram_bot.rabbitmq_utils import RabbitMQClient
from parser.news_parser import NewsParser
from parser.categories import CategoryStructure

# Initialize components
news_parser = NewsParser()
rabbitmq_client = RabbitMQClient()
category_structure = CategoryStructure()

# Constants
ARTICLES_QUEUE = "new_articles"               # Очередь для новых статей
CHECK_INTERVAL = 1800                         # Интервал проверки новостей (30 минут)
PUBLISH_DELAY = 2                            # Задержка между публикациями в очередь (секунды)

async def publish_article_to_queue(article: Dict, category_name: str) -> None:
    """
    Публикация статьи в очередь с задержкой
    
    Args:
        article (Dict): Данные статьи
        category_name (str): Название категории
    """
    if not article.get('url') or not article.get('title'):
        return

    try:
        article_data = {
            "article": article,
            "category_name": category_name
        }
        
        await rabbitmq_client.publish_message(ARTICLES_QUEUE, article_data)
        
        # Добавляем небольшую задержку, чтобы не перегружать очередь
        await asyncio.sleep(PUBLISH_DELAY)
        
    except Exception as e:
        logging.error(f"Error publishing article to queue: {e}")

async def check_category_for_news(cat_path: Tuple[str, ...]) -> None:
    """
    Проверка категории на наличие новых статей
    
    Args:
        cat_path (Tuple[str, ...]): Путь категории (cat_lv1, cat_lv2, cat_lv3)
    """
    try:
        category_name = " > ".join([
            category_structure.get_category_name(*cat_path[:i+1]) or cat_path[i]
            for i in range(len(cat_path))
        ])
        
        articles_found = False
        today = datetime.now().date()
          # Создаем буфер для статей
        new_articles = []
        
        async for article in news_parser.stream_articles_by_category(
            cat_lv1=cat_path[0],
            cat_lv2=cat_path[1] if len(cat_path) > 1 else None,
            cat_lv3=cat_path[2] if len(cat_path) > 2 else None
        ):
            if not article.get('title') or not article.get('url'):
                continue

            # Parse article date and skip old articles early
            pub_date = None
            if article.get('publication_date'):
                try:
                    pub_date = datetime.fromisoformat(article['publication_date']).date()
                except (ValueError, TypeError):
                    continue

            # Only process today's articles
            if not pub_date or pub_date != today:
                continue

            articles_found = True
            new_articles.append(article)

        # Если нашли статьи, публикуем их в очередь
        if new_articles:
            for article in new_articles:
                await publish_article_to_queue(article, category_name)
            logging.info(f"Published {len(new_articles)} new articles from category: {category_name}")

    except Exception as e:
        logging.error(f"Error checking category {cat_path}: {e}")

async def check_all_categories() -> None:
    """Проверка всех категорий на наличие новых новостей"""
    try:
        # Получаем все категории третьего уровня
        for cat_lv1, cat_data in category_structure.categories.items():
            if not cat_data.get('subcategories'):
                continue
                
            for cat_lv2, lv2_data in cat_data['subcategories'].items():
                if not lv2_data.get('subcategories'):
                    continue
                    
                for cat_lv3 in lv2_data['subcategories'].keys():
                    await check_category_for_news((cat_lv1, cat_lv2, cat_lv3))
                    # Небольшая задержка между категориями
                    await asyncio.sleep(5)

    except Exception as e:
        logging.error(f"Error checking categories: {e}")

async def start_parser_service():
    """
    Запуск сервиса парсера
    """
    try:
        # Подключаемся к RabbitMQ
        await rabbitmq_client.connect()
        
        # Объявляем очередь для статей
        await rabbitmq_client.declare_queue(ARTICLES_QUEUE)
        
        logging.info("Parser service started successfully")
        
        # Основной цикл работы сервиса
        while True:
            try:
                logging.info("Starting news check cycle")
                await check_all_categories()
                logging.info(f"News check complete. Waiting {CHECK_INTERVAL} seconds until next check.")
                await asyncio.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                logging.error(f"Error in news check cycle: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
            
    except Exception as e:
        logging.error(f"Error in parser service: {e}")
        raise

if __name__ == "__main__":
    # Очищаем существующие хендлеры
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(start_parser_service())
