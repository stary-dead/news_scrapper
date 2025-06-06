from parser.categories import CategoryStructure
import httpx
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import time
from .models import NewsArticle
import logging
import json
import os


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

    async def _get_page_content(self, url: str) -> str:
        """Get page content asynchronously"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=10.0) as client:
                    await asyncio.sleep(1)  # Delay between requests
                    response = await client.get(url)
                    
                    # Handle common HTTP errors
                    if response.status_code == 404:
                        self.logger.error(f"Page not found: {url}")
                        return None
                    elif response.status_code == 403:
                        self.logger.error(f"Access forbidden: {url}")
                        return None
                    elif response.status_code != 200:
                        self.logger.error(f"HTTP error {response.status_code} for {url}")
                        retry_count += 1
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                        continue
                    
                    return response.text
            except httpx.TimeoutException:
                self.logger.error(f"Timeout while fetching {url}")
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)
            except httpx.RequestError as e:
                self.logger.error(f"Error getting page {url}: {e}")
                retry_count += 1
                await asyncio.sleep(2 ** retry_count)
            except Exception as e:
                self.logger.error(f"Unexpected error while fetching {url}: {e}")
                return None
        
        self.logger.error(f"Failed to fetch {url} after {max_retries} retries")
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
            
        # Convert URL to lowercase for case-insensitive comparison
        url_lower = url.lower()
        
        # Accept both relative and absolute URLs from rp.pl
        if not (url_lower.startswith('/') or url_lower.startswith('https://www.rp.pl')):
            self.logger.debug(f"Skipping external URL: {url}")
            return False
            
        # Skip certain file types and special paths
        if any(ext in url_lower for ext in ['.jpg', '.pdf', '.png', '.xml', 'rss', 'feed']):
            self.logger.debug(f"Skipping file/feed URL: {url}")
            return False

        # Skip special sections and system pages
        special_sections = [
            '/logowanie',
            '/moj-profil',
            '/mapa-strony',
            '/regulamin',
            '/rodo'
        ]
        
        if any(section in url_lower for section in special_sections):
            self.logger.debug(f"Skipping special section: {url}")
            return False

        # Check if URL contains article ID pattern (e.g., /art42380421)
        import re
        if '/art' in url_lower and re.search(r'/art\d+', url_lower):
            self.logger.debug(f"Valid article URL found: {url}")
            return True
            
        self.logger.debug(f"Invalid article URL (no article ID): {url}")
        return False

    async def _parse_article_data(self, article_element: BeautifulSoup, url: str) -> NewsArticle:
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
                "header h1",
                "h1.contentTitle"  # Added additional selector
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
                ".article-description",
                "div.article--element--text--subtitle",  # Added additional selector
                "div.lead"  # Added additional selector
            ]
            for selector in subtitle_selectors:
                subtitle = article_element.select_one(selector)
                if subtitle:
                    subtitle_text = subtitle.text.strip()
                    break

            # Publication and update dates
            pub_date = article_element.select_one("#livePublishedAtContainer")
            if not pub_date:
                # Try alternative date selectors
                date_selectors = [
                    "time.article--time",
                    "span.article--published",
                    "div.article--published"
                ]
                for selector in date_selectors:
                    pub_date = article_element.select_one(selector)
                    if pub_date:
                        break

            update_date = article_element.select_one("#liveRetainAtContainerInner")

            # Image and its description
            image = None
            # Try to find image in blog--image div first
            blog_image_div = article_element.select_one("div.blog--image")
            if blog_image_div:
                image = blog_image_div.select_one("img")
            # If not found, try other selectors
            if not image:
                image_selectors = [
                    "picture img",
                    "div.article--image img",
                    "div.article--media img",
                    ".article--top--image img",
                    "figure.main-photo img"
                ]
                for selector in image_selectors:
                    image = article_element.select_one(selector)
                    if image:
                        break
            
            image_desc = article_element.select_one("p.article--media--lead")
            if not image_desc:
                image_desc = article_element.select_one("figcaption.image-description")

            image_author = article_element.select_one("p.image--author")
            if not image_author:
                image_author = article_element.select_one("div.image-author")

            # Author of the article
            author = None
            author_selectors = [
                "div.author p.name a",
                "div.article--author p.name",
                "div.article--author a",
                "div.author-name",
                "p.article--author"
            ]
            for selector in author_selectors:
                author = article_element.select_one(selector)
                if author:
                    break

            # Breadcrumbs
            breadcrumbs = []
            crumb_container = article_element.select_one("ul.breadcrumb--component")
            if crumb_container:
                for crumb in crumb_container.select("li a"):
                    breadcrumbs.append({
                        'text': crumb.text.strip(),
                        'url': urljoin(self.base_url, crumb.get('href', ''))
                    })

            # Full article text
            full_text_parts = []
            intro_text_parts = []
            
            # Get intro/lead text first
            intro_selectors = [
                "div.intro--body--text--fadeOut p.articleBodyBlock",
                "div.article-lead p",
                "div.lead p",
                "div.article__lead p",
                "div.article-intro p"
            ]
            
            for selector in intro_selectors:
                intro_blocks = article_element.select(selector)
                if intro_blocks:
                    for block in intro_blocks:
                        text = block.get_text(strip=True)
                        if text:
                            intro_text_parts.append(text)
                    break

            # Get article content
            content = None
            content_selectors = [
                "div.article--content.mx-auto.my-0",
                "div.article-body",
                "div.article--content",
                "div.article--text",
                "article.article-content",
                "div.blog--content",
                "div.contentBody",
                "div[itemprop='articleBody']",  # Schema.org markup
                "article[itemprop='articleBody']",
                "div.article__content",
                "div.article-text",
                "#article-body",
                "main article"
            ]
            
            for selector in content_selectors:
                content = article_element.select_one(selector)
                if content:
                    self.logger.info(f"Found article content with selector: {selector}")
                    break

            if content:
                # First, remove unnecessary elements
                for element in content.select("script, style, iframe, .advertisement, .social-share, .related-articles"):
                    element.decompose()

                # Get the lead/intro paragraph if it exists and wasn't found earlier
                if not intro_text_parts:
                    lead_selectors = [
                        "div.lead", 
                        "div.article-lead",
                        "p.lead",
                        "div.article__lead"
                    ]
                    for selector in lead_selectors:
                        lead = content.select_one(selector)
                        if lead:
                            lead_text = lead.get_text(strip=True)
                            if lead_text:
                                intro_text_parts.append(lead_text)
                            break

                # Get all text-containing elements
                for element in content.find_all(['p', 'h2', 'h3', 'h4', 'li', 'blockquote']):
                    # Skip if element is part of unwanted content
                    if element.find_parent(class_=['image-caption', 'article-tags', 'social-share', 'related-articles']):
                        continue
                    
                    # Get text and clean it
                    text = element.get_text(strip=True)
                    if text and len(text) > 1:  # Skip single characters
                        full_text_parts.append(text)

            # If no structured content found, try getting all text content
            if not full_text_parts:
                # Try finding article text in any div with substantial content
                for div in article_element.find_all('div', recursive=False):
                    text = div.get_text(strip=True)
                    if len(text) > 200:  # Only include substantial blocks of text
                        full_text_parts.append(text)

            # Get author information with more selectors
            author = None
            author_selectors = [
                "div.author p.name a",
                "div.article--author p.name",
                "div.article--author a",
                "div.author-name",
                "p.article--author",
                "span.article__author",
                "div[itemprop='author']",
                ".article-author",
                ".author-info"
            ]
            
            for selector in author_selectors:
                author = article_element.select_one(selector)
                if author:
                    author_text = author.get_text(strip=True)
                    if author_text:
                        self.logger.info(f"Found author: {author_text}")
                        break

            # More comprehensive image search
            image = None
            image_url = None
            
            # Try multiple image sources
            image_selectors = [
                "div.blog--image img",
                "picture img",
                "div.article--image img",
                "div.article--media img",
                ".article--top--image img",
                "figure.main-photo img",
                "div[itemprop='image'] img",
                ".article__image img",
                "meta[property='og:image']"  # OpenGraph image
            ]
            
            for selector in image_selectors:
                image = article_element.select_one(selector)
                if image:
                    if 'content' in image.attrs:  # For meta tags
                        image_url = image['content']
                    elif 'src' in image.attrs:
                        image_url = image['src']
                    elif 'data-src' in image.attrs:
                        image_url = image['data-src']
                        
                    if image_url:
                        self.logger.info(f"Found image: {image_url}")
                        break

            return NewsArticle(
                title=title_text,
                subtitle=subtitle_text,
                url=url,
                publication_date=self._parse_datetime(pub_date.text.strip() if pub_date else None),
                update_date=self._parse_datetime(update_date.text.strip() if update_date else None),
                image_url=image_url,
                image_description=image_desc.text.strip() if image_desc else None,
                image_author=image_author.text.strip() if image_author else None,
                author=author.text.strip() if author else None,
                breadcrumbs=breadcrumbs,
                intro_text="\n".join(intro_text_parts) if intro_text_parts else None,
                full_text="\n\n".join(full_text_parts) if full_text_parts else None
            )
        except Exception as e:
            self.logger.error(f"Error parsing article {url}: {str(e)}")
            return None

    async def parse_by_category(self, cat_lv1: str = None, cat_lv2: str = None, cat_lv3: str = None, 
                              limit: int = 5, save_to_file: bool = True) -> dict:
        """Parse news by specified categories asynchronously"""
        try:
            # Forming URL for the category
            category_path = '/'.join(filter(None, [cat_lv1, cat_lv2, cat_lv3]))
            category_url = urljoin(self.base_url, category_path)
            
            self.logger.info(f"Requesting category page: {category_url}")
            html = await self._get_page_content(category_url)
            
            if not html:
                self.logger.error(f"Failed to retrieve category page: {category_url}")
                return {
                    "error": "Failed to retrieve category page",
                    "category_url": category_url,
                    "category_path": category_path
                }
            self.logger.info("Category page successfully retrieved")
            soup = BeautifulSoup(html, 'html.parser')
            
            # First find all content blocks that contain articles
            article_blocks = []
            block_selectors = [
                "div[data-gtm-placement^='type:content/position:']",  # Main blocks with position
                "div.content--block",  # All content blocks
                "div[data-mrf-recirculation^='Category / ListOfArticles']"  # Additional blocks
            ]
            
            self.logger.info("Looking for article blocks...")
            for selector in block_selectors:
                blocks = soup.select(selector)
                self.logger.info(f"Found {len(blocks)} blocks with selector: {selector}")
                for block in blocks:
                    self.logger.debug(f"Block HTML: {block}")
                article_blocks.extend(blocks)            # Then find links within these blocks
            article_links = []
            link_selectors = [
                "a.contentLink[href][data-gtm-trigger='title']",  # Main content links
                "a[href][cmp-ltrk^='Category / ListOfArticles']",  # Category list articles
                "a[href][data-mrf-link]"  # Links with mrf tracking
            ]
            self.logger.info("Looking for article links within blocks...")
            for block in article_blocks:
                # Log the block class and data attributes for debugging
                self.logger.info(f"Processing block: class='{block.get('class', [])}' data-gtm-placement='{block.get('data-gtm-placement', '')}'")
                
                for selector in link_selectors:
                    links = block.select(selector)
                    if links:
                        self.logger.info(f"Found {len(links)} raw links with selector '{selector}'")
                        for link in links:
                            url = link.get('href', '')
                            is_valid = self._is_valid_article_url(url)
                            self.logger.info(f"URL: {url} - Valid: {is_valid}")
                            
                        filtered_links = [link for link in links if self._is_valid_article_url(link.get('href', ''))]
                        if filtered_links:
                            self.logger.info(f"Found {len(filtered_links)} valid links in block using selector: {selector}")
                            for link in filtered_links:
                                self.logger.info(f"Adding valid link: {link.get('href', '')}")
                        article_links.extend(filtered_links)

            # Check if we found any articles
            if not article_links:
                self.logger.warning(f"No articles found in category: {category_path}")
                return {
                    "category_url": category_url,
                    "articles_found": 0,
                    "category_path": category_path,
                    "parsed_at": datetime.now().isoformat(),
                    "articles": []
                }

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

            # Process articles concurrently with rate limiting
            tasks = []
            semaphore = asyncio.Semaphore(3)  # Limit concurrent requests to 3

            async def fetch_with_semaphore(url):
                try:
                    async with semaphore:
                        return await self._parse_article_data(
                            BeautifulSoup(await self._get_page_content(url), 'html.parser'),
                            url
                        )
                except Exception as e:
                    self.logger.error(f"Error fetching article {url}: {e}")
                    return None

            for url in article_urls:
                tasks.append(fetch_with_semaphore(url))

            articles = []
            results = await asyncio.gather(*tasks, return_exceptions=True)
            articles = []
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Error processing article: {result}")
                    continue
                if result:
                    articles.append(result.to_dict())

            result = {
                "category_url": category_url,
                "articles_found": len(articles),
                "category_path": category_path,
                "parsed_at": datetime.now().isoformat(),
                "articles": articles
            }

            if save_to_file and articles:
                self.save_to_json(result, category_path)

            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing category {category_path}: {e}")
            return {
                "error": str(e),
                "category_url": category_url if 'category_url' in locals() else None,
                "category_path": category_path if 'category_path' in locals() else None
            }

    async def stream_articles_by_category(self, cat_lv1: str = None, cat_lv2: str = None, cat_lv3: str = None):
        """Parse and yield news articles one by one as they are parsed
        
        Args:
            cat_lv1 (str, optional): Level 1 category
            cat_lv2 (str, optional): Level 2 category
            cat_lv3 (str, optional): Level 3 category
            
        Yields:
            dict: Article data as it becomes available
        """
        try:
            # Forming URL for the category
            category_path = '/'.join(filter(None, [cat_lv1, cat_lv2, cat_lv3]))
            category_url = urljoin(self.base_url, category_path)
            
            self.logger.info(f"Requesting category page: {category_url}")
            html = await self._get_page_content(category_url)
            
            if not html:
                self.logger.error(f"Failed to retrieve category page: {category_url}")
                return

            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all article links
            article_links = []
            article_blocks = []
            
            # Find content blocks
            block_selectors = [
                "div[data-gtm-placement^='type:content/position:']",
                "div.content--block",
                "div[data-mrf-recirculation^='Category / ListOfArticles']"
            ]
            
            for selector in block_selectors:
                blocks = soup.select(selector)
                article_blocks.extend(blocks)

            # Find links within blocks
            link_selectors = [
                "a.contentLink[href][data-gtm-trigger='title']",
                "a[href][cmp-ltrk^='Category / ListOfArticles']",
                "a[href][data-mrf-link]"
            ]
            
            for block in article_blocks:
                for selector in link_selectors:
                    links = block.select(selector)
                    article_links.extend([
                        link for link in links 
                        if self._is_valid_article_url(link.get('href', ''))
                    ])

            # Process articles one by one with rate limiting
            semaphore = asyncio.Semaphore(1)  # Process one article at a time
            
            for link in article_links:
                url = urljoin(self.base_url, link.get('href', ''))
                
                try:
                    async with semaphore:
                        article_html = await self._get_page_content(url)
                        if not article_html:
                            continue
                            
                        article_soup = BeautifulSoup(article_html, 'html.parser')
                        article = await self._parse_article_data(article_soup, url)
                        
                        if article:
                            yield article.to_dict()
                            
                except Exception as e:
                    self.logger.error(f"Error processing article {url}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error in stream_articles_by_category: {e}")
            return

    def save_to_json(self, data: dict, category_path: str) -> str:
        """Save parsed articles to a JSON file
        
        Args:
            data: Dictionary containing articles and metadata
            category_path: Category path used for the filename
            
        Returns:
            str: Path to the saved JSON file
        """
        # Create data/articles directory if it doesn't exist
        os.makedirs("data/articles", exist_ok=True)
        
        # Create a filename based on category and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_category = category_path.replace("/", "_").strip("_")
        filename = f"data/articles/{safe_category}_{timestamp}.json"
        
        # Save the data
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        self.logger.info(f"Articles saved to {filename}")
        return filename

    def add_category(self, parent_code: str = None, code: str = None, name: str = None) -> bool:
        """Add new category"""
        return self.category_structure.add_category(parent_code, code, name)

    def save_articles_to_json(self, articles: list, file_path: str) -> bool:
        """Save parsed articles to a JSON file"""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(articles, json_file, ensure_ascii=False, indent=4)
            
            self.logger.info(f"Articles successfully saved to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving articles to JSON: {str(e)}")
            return False


# Example usage:
if __name__ == "__main__":
    parser = NewsParser()
    
    # Example parsing by categories with specified number of news
    async def main():
        result = await parser.parse_by_category(
            cat_lv1="ekonomia",
            cat_lv2="biznes",
            cat_lv3="eksport",
            limit=3,
            save_to_file=True  # Enable saving to JSON
        )
        
        # Output results
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nArticles found: {result['articles_found']}")
            print(f"Category URL: {result['category_url']}")
            print(f"Results saved in data/articles directory\n")
            
            for article in result['articles']:
                print("=" * 100)
                print(f"Title: {article['title']}")
                print(f"Subtitle: {article['subtitle']}")
                print(f"Publication date: {article['publication_date']}")
                print(f"Author: {article['author']}")
                print(f"URL: {article['url']}")
                print(f"Image URL: {article['image_url']}")
                print("-" * 50)
                
                if article['full_text']:
                    print("\nFull article text:")
                    print("-" * 30)
                    print(article['full_text'])
                elif article['intro_text']:
                    print("\nArticle introduction:")
                    print("-" * 30)
                    print(article['intro_text'])
                    print("\nNote: Full article text is not available (possible paywall)")
                else:
                    print("\nNo article text available")
                
                print("=" * 100)
                print("\n")

    # Run the async main function
    asyncio.run(main())
