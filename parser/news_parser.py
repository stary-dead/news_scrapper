from categories import CategoryStructure
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import time
from models import NewsArticle
import logging


class NewsParser:
    def __init__(self):
        self.category_structure = CategoryStructure()
        self.base_url = "https://www.rp.pl"  # Added www since site redirects to it
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Add console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def _get_page_content(self, url: str) -> str:
        """Get page content"""
        try:
            time.sleep(1)  # Delay between requests
            response = requests.get(url, headers=self.headers, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Error getting page {url}: {e}")
            return None

    def _parse_datetime(self, date_str: str) -> datetime:
        """Parse date from string"""
        try:
            return datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            return None

    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article link"""
        if not url:
            return False

        # Check if URL leads to an article
        article_indicators = [
            '/art',  # Standard article indicator
            '/ekonomia/',  # Economy section
            '/biznes/',    # Business section
            '/eksport/'    # Export section
        ]
        
        return any(indicator in url.lower() for indicator in article_indicators)

    def _parse_article_data(self, article_element: BeautifulSoup, url: str) -> NewsArticle:
        """Parse single article data"""
        try:
            self.logger.info(f"Parsing article: {url}")

            # Get title
            title_text = None
            title_selectors = [
                "h1.articleTitle",
                "h1.blog--title",
                "h1.article--title",
                "div.article--title",
                "header h1"
            ]
            for selector in title_selectors:
                title = article_element.select_one(selector)
                if title:
                    title_text = title.text.strip()
                    self.logger.info(f"Found title: {title_text}")
                    break

            # Subtitle
            subtitle_text = None
            subtitle_selectors = [
                "div.blog--subtitle",
                "div.article--subtitle",
                ".article--lead",
                ".article-description"
            ]
            for selector in subtitle_selectors:
                subtitle = article_element.select_one(selector)
                if subtitle:
                    subtitle_text = subtitle.text.strip()
                    break

            # Publication and update dates
            pub_date = article_element.select_one("#livePublishedAtContainer")
            update_date = article_element.select_one("#liveRetainAtContainerInner")

            # Image and its description
            image = article_element.select_one("picture img") or article_element.select_one("div.blog--image img")
            image_desc = article_element.select_one("p.article--media--lead")
            image_author = article_element.select_one("p.image--author")

            # Author of the article
            author = article_element.select_one("div.author p.name a")

            # Breadcrumbs
            breadcrumbs = []
            crumb_container = article_element.select_one("ul.breadcrumb--component")
            if crumb_container:
                for crumb in crumb_container.select("li a"):
                    breadcrumbs.append({
                        'text': crumb.text.strip(),
                        'url': urljoin(self.base_url, crumb.get('href', ''))
                    })

            # Introductory text
            intro_text = []
            intro_block = article_element.select_one("div.intro--body--text--fadeOut")
            if intro_block:
                for p in intro_block.select("p.articleBodyBlock"):
                    intro_text.append(p.text.strip())

            return NewsArticle(
                title=title_text,
                subtitle=subtitle_text,
                url=url,
                publication_date=self._parse_datetime(pub_date.text.strip() if pub_date else None),
                update_date=self._parse_datetime(update_date.text.strip() if update_date else None),
                image_url=image.get('src') if image else None,
                image_description=image_desc.text.strip() if image_desc else None,
                image_author=image_author.text.strip() if image_author else None,
                author=author.text.strip() if author else None,
                breadcrumbs=breadcrumbs,
                intro_text="\n".join(intro_text) if intro_text else None
            )
        except Exception as e:
            self.logger.error(f"Error parsing article {url}: {str(e)}")
            return None

    def parse_by_category(self, cat_lv1: str = None, cat_lv2: str = None, cat_lv3: str = None, 
                         limit: int = 5) -> dict:
        """Parse news by specified categories"""
        # Forming URL for the category
        category_path = '/'.join(filter(None, [cat_lv1, cat_lv2, cat_lv3]))
        category_url = urljoin(self.base_url, category_path)
        
        self.logger.info(f"Requesting category page: {category_url}")
        html = self._get_page_content(category_url)
        if not html:
            return {"error": "Failed to retrieve category page"}
        
        self.logger.info("Category page successfully retrieved")
        soup = BeautifulSoup(html, 'html.parser')

        # Looking for articles using various selectors
        article_links = []
        article_selectors = [
            "div[data-mrf-section='Category / ListOfArticles'] a[href]",  # Main article container
            "div[data-gtm-placement^='type:content'] a[href]",  # Containers with GTM markup
            "div[data-mrf-recirculation*='Category / ListOfArticles'] a[href]",  # Additional articles
            "div.content--block a[href]"  # Content blocks
        ]

        # Filtering links by selectors
        for selector in article_selectors:
            links = soup.select(selector)
            if links:
                filtered_links = [link for link in links if self._is_valid_article_url(link.get('href', ''))]
                self.logger.info(f"Found {len(filtered_links)} valid links for selector {selector}")
                article_links.extend(filtered_links)

        # Processing found links
        article_urls = []
        seen_urls = set()
        
        self.logger.info(f"Total links found: {len(article_links)}")
        
        # Filtering and checking links
        for link in article_links:
            if len(article_urls) >= limit:
                break
            
            url = urljoin(self.base_url, link.get('href', ''))
            
            if url not in seen_urls and self._is_valid_article_url(url):
                self.logger.info(f"Adding article: {url}")
                article_urls.append(url)
                seen_urls.add(url)

        # Collecting article data
        articles = []
        for url in article_urls:
            html = self._get_page_content(url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                article_data = self._parse_article_data(soup, url)
                if article_data:
                    articles.append(article_data.to_dict())
                    self.logger.info(f"Successfully processed article: {url}")

        return {
            "category_url": category_url,
            "articles_found": len(articles),
            "articles": articles
        }

    def add_category(self, parent_code: str = None, code: str = None, name: str = None) -> bool:
        """Add new category"""
        return self.category_structure.add_category(parent_code, code, name)


# Example usage:
if __name__ == "__main__":
    parser = NewsParser()
    
    # Example parsing by categories with specified number of news
    result = parser.parse_by_category(
        cat_lv1="ekonomia",
        cat_lv2="biznes",
        cat_lv3="eksport",
        limit=3  # Get 7 latest news
    )
    
    # Output results
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\nArticles found: {result['articles_found']}")
        print(f"Category URL: {result['category_url']}\n")
        
        for article in result['articles']:
            print(f"Title: {article['title']}")
            print(f"Subtitle: {article['subtitle']}")
            print(f"Publication date: {article['publication_date']}")
            print(f"Author: {article['author']}")
            print(f"URL: {article['url']}")
            print("-" * 80)
