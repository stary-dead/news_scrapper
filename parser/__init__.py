"""
Parser package for news scrapping from rp.pl
Provides functionality for category management and news extraction
"""

from parser.categories import CategoryStructure
from parser.models import NewsArticle
from parser.news_parser import NewsParser
from parser.category_scraper import CategoryScraper

__all__ = [
    'CategoryStructure',
    'NewsArticle',
    'NewsParser',
    'CategoryScraper'
]

# Версия пакета
__version__ = '0.1.0'