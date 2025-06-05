"""
Parser package for news scrapping from rp.pl
Provides functionality for category management and news extraction
"""

from .categories import CategoryStructure
from .models import NewsArticle
from .news_parser import NewsParser
from .category_scraper import CategoryScraper

__all__ = [
    'CategoryStructure',
    'NewsArticle',
    'NewsParser',
    'CategoryScraper'
]

# Версия пакета
__version__ = '0.1.0'