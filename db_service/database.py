import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from .models import Base, Article

class DatabaseService:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        
    def init_db(self):
        """Инициализация базы данных"""
        Base.metadata.create_all(self.engine)
        
    async def save_article(self, article_data: dict, category_name: str) -> bool:
        """
        Сохранение статьи в базу данных
        
        Args:
            article_data (dict): Данные статьи
            category_name (str): Название категории
            
        Returns:
            bool: True если статья успешно сохранена, False если статья уже существует
        """
        session = self.Session()
        try:
            # Преобразуем дату публикации
            pub_date = datetime.fromisoformat(article_data['publication_date'])
            
            article = Article(
                title=article_data['title'],
                url=article_data['url'],
                content=article_data.get('content'),
                category_name=category_name,
                publication_date=pub_date,
                processed=False,
                image_url=article_data.get('image_url'),
                author=article_data.get('author')
            )
            
            session.add(article)
            session.commit()
            return True
            
        except IntegrityError:
            # Статья с таким URL уже существует
            session.rollback()
            return False
            
        except Exception as e:
            session.rollback()
            logging.error(f"Error saving article: {e}")
            return False
            
        finally:
            session.close()
            
    async def get_unprocessed_articles(self, limit: int = 10):
        """
        Получение необработанных статей
        
        Args:
            limit (int): Максимальное количество статей
            
        Returns:
            List[Article]: Список необработанных статей
        """
        session = self.Session()
        try:
            articles = session.query(Article)\
                .filter_by(processed=False)\
                .order_by(Article.publication_date.asc())\
                .limit(limit)\
                .all()
            # Make sure to convert articles to dicts before closing session
            article_dicts = [article.to_dict() for article in articles]
            return article_dicts
        finally:
            session.close()
            
    async def mark_article_as_processed(self, article_id: int):
        """
        Отметить статью как обработанную
        
        Args:
            article_id (int): ID статьи
        """
        session = self.Session()
        try:
            article = session.query(Article).filter_by(id=article_id).first()
            if article:
                article.processed = True
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    logging.error(f"Error committing article update: {e}")
                    raise
        finally:
            session.close()
