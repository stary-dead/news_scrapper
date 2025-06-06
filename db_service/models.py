from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    category_name = Column(String(200), nullable=False)
    publication_date = Column(DateTime, nullable=False)
    processed = Column(Boolean, default=False)  # Флаг, была ли статья отправлена в Telegram
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    image_url = Column(String(500), nullable=True)
    author = Column(String(200), nullable=True)

    # Создаем уникальный индекс по URL, чтобы избежать дубликатов
    __table_args__ = (
        UniqueConstraint('url', name='unique_article_url'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'content': self.content,
            'category_name': self.category_name,
            'publication_date': self.publication_date.isoformat(),
            'processed': self.processed,
            'created_at': self.created_at.isoformat(),
            'image_url': self.image_url,
            'author': self.author
        }
