import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import time
from urllib.parse import urljoin
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CategoryScraper:
    def __init__(self):
        self.base_url = "https://rp.pl"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.categories = {}
        self.visited_urls = set()

    def get_page_content(self, url):
        """Get page content with error handling and delay"""
        try:
            time.sleep(2)  # Delay between requests
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error getting page {url}: {e}")
            return None

    def extract_categories(self, html, selector):
        """Extract categories from HTML by selector"""
        soup = BeautifulSoup(html, 'html.parser')
        categories_ul = soup.select_one(selector)
        if not categories_ul:
            return []

        categories = []
        for item in categories_ul.find_all('li'):
            link = item.find('a')
            if link:
                url = urljoin(self.base_url, link.get('href', ''))
                name = link.get_text(strip=True)
                code = url.rstrip('/').split('/')[-1].lower()
                if code and name:
                    categories.append({
                        'url': url,
                        'name': name,
                        'code': code
                    })
        return categories

    def process_subcategories(self, parent_code, url, level=1, max_level=3):
        """Recursive processing of subcategories"""
        if level > max_level or url in self.visited_urls:
            return {}
        
        self.visited_urls.add(url)
        logger.info(f"Processing level {level}, URL: {url}")
        
        html = self.get_page_content(url)
        if not html:
            return {}

        categories = self.extract_categories(
            html,
            'ul[data-gtm-section="page:header/section:navigation"][class="header--categories headerCategories"]'
        )

        subcategories = {}
        for category in categories:
            subcats = self.process_subcategories(
                category['code'],
                category['url'],
                level + 1,
                max_level
            )
            subcategories[category['code']] = {
                'name': category['name'],
                'subcategories': subcats
            }

        return subcategories

    def scrape_categories(self):
        """Main method for collecting all categories"""
        logger.info("Starting category collection")
        html = self.get_page_content(self.base_url)
        if not html:
            return

        # Получаем категории первого уровня
        categories = self.extract_categories(
            html,
            'ul[data-mrf-section="ignored"][data-gtm-section="page:header/section:navigation"][class="header--categories headerCategories"]'
        )

        # Обрабатываем каждую категорию первого уровня
        for category in categories:
            subcats = self.process_subcategories(
                category['code'],
                category['url']
            )
            self.categories[category['code']] = {
                'name': category['name'],
                'subcategories': subcats
            }

    def save_categories(self):
        """Сохранение категорий в JSON файл"""
        json_path = Path(__file__).parent / 'data' / 'categories.json'
        json_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=4)
            logger.info(f"Категории успешно сохранены в {json_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении категорий: {e}")

def main():
    scraper = CategoryScraper()
    scraper.scrape_categories()
    scraper.save_categories()

if __name__ == "__main__":
    main()
