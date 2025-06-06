import pytest
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from parser.news_parser import NewsParser
from parser.models import NewsArticle
import json
import os

# Пример HTML статьи для тестов
SAMPLE_ARTICLE_HTML = '''
<!DOCTYPE html>
<html>
<body>
    <h1 class="article--title">Тестовый заголовок статьи</h1>
    <div class="article--subtitle">Подзаголовок тестовой статьи</div>
    
    <div id="livePublishedAtContainer">05.06.2025 14:30</div>
    <div id="liveRetainAtContainerInner">05.06.2025 15:00</div>
    
    <div class="blog--image">
        <img src="https://example.com/image.jpg" alt="Test image">
    </div>
    <p class="article--media--lead">Описание изображения</p>
    <p class="image--author">Автор фото</p>
    
    <div class="author">
        <p class="name"><a href="/author/test">Иван Иванов</a></p>
    </div>
    
    <ul class="breadcrumb--component">
        <li><a href="/ekonomia">Экономика</a></li>
        <li><a href="/ekonomia/biznes">Бизнес</a></li>
    </ul>
    
    <div class="article--content mx-auto my-0">
        <p>Первый параграф статьи</p>
        <p>Второй параграф статьи</p>
    </div>
    
    <div class="intro--body--text--fadeOut">
        <p class="articleBodyBlock">Вводный текст статьи</p>
    </div>
</body>
</html>
'''

# Пример HTML страницы категории для тестов
SAMPLE_CATEGORY_HTML = '''
<!DOCTYPE html>
<html>
<body>
    <div class="content--block">
        <a href="/ekonomia/art12345" class="contentLink" data-gtm-trigger="title">Статья 1</a>
        <a href="/ekonomia/art67890" class="contentLink" data-gtm-trigger="title">Статья 2</a>
    </div>
</body>
</html>
'''

@pytest.fixture
def news_parser():
    return NewsParser()

@pytest.fixture
def sample_article_soup():
    return BeautifulSoup(SAMPLE_ARTICLE_HTML, 'html.parser')

@pytest.mark.asyncio
async def test_parse_article_data_full(news_parser, mocker):
    """Тест проверяет корректность парсинга всех полей статьи с реального URL"""
    url = "https://www.rp.pl/polityka/art42484221-dariusz-lasocki-byly-czlonek-pkw-o-komisji-95-w-krakowie-po-prostu-sie-pomylili"
    
    # Сначала получаем реальный HTML-контент статьи
    html_content = await news_parser._get_page_content(url)
    assert html_content is not None, "Не удалось получить контент статьи"
    
    # Создаем soup из полученного HTML
    article_soup = BeautifulSoup(html_content, 'html.parser')
    
    # Парсим статью
    article = await news_parser._parse_article_data(article_soup, url)
    
    # Проверяем базовые поля
    assert isinstance(article, NewsArticle)
    assert article.url == url
    assert article.title is not None and len(article.title) > 0
    
    # Проверяем наличие текста статьи
    assert article.full_text is not None and len(article.full_text) > 0
    
    # Проверяем формат даты публикации
    if article.publication_date:
        assert isinstance(article.publication_date, datetime)
        
    # Проверяем breadcrumbs
    assert article.breadcrumbs is not None
    assert len(article.breadcrumbs) > 0
    assert all(isinstance(crumb, dict) for crumb in article.breadcrumbs)
    assert all('text' in crumb and 'url' in crumb for crumb in article.breadcrumbs)

@pytest.mark.asyncio
async def test_parse_article_data_minimal(news_parser):
    """Тест проверяет работу парсера с минимальным набором данных"""
    minimal_html = '''
    <html>
        <h1 class="article--title">Минимальный заголовок</h1>
        <div class="article--content">
            <p>Минимальный текст</p>
        </div>
    </html>
    '''
    soup = BeautifulSoup(minimal_html, 'html.parser')
    article = await news_parser._parse_article_data(soup, "https://www.rp.pl/test")
    
    assert isinstance(article, NewsArticle)
    assert article.title == "Минимальный заголовок"
    assert article.full_text == "Минимальный текст"
    assert article.subtitle is None
    assert article.image_url is None
    assert article.author is None

@pytest.mark.asyncio
async def test_invalid_date_handling(news_parser):
    """Тест проверяет обработку некорректных дат"""
    html = '''
    <html>
        <h1 class="article--title">Тест даты</h1>
        <div id="livePublishedAtContainer">invalid-date</div>
    </html>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    article = await news_parser._parse_article_data(soup, "https://www.rp.pl/test")
    
    assert article.publication_date is None

def test_valid_article_url(news_parser):
    """Тест проверяет валидацию URL статей"""
    assert news_parser._is_valid_article_url("https://www.rp.pl/ekonomia/art12345")
    assert news_parser._is_valid_article_url("/ekonomia/art12345")
    assert not news_parser._is_valid_article_url("https://www.rp.pl/image.jpg")
    assert not news_parser._is_valid_article_url("https://www.rp.pl/logowanie")
    assert not news_parser._is_valid_article_url("https://other-site.com/art12345")

@pytest.mark.asyncio
async def test_parse_by_category_error_handling(news_parser, mocker):
    """Тест проверяет обработку ошибок при парсинге категории"""
    mocker.patch.object(news_parser, '_get_page_content', return_value=None)
    
    result = await news_parser.parse_by_category("ekonomia", "biznes")
    
    assert "error" in result
    assert result["category_path"] == "ekonomia/biznes"

@pytest.mark.asyncio
async def test_stream_articles_by_category(news_parser, mocker):
    """Тест проверяет потоковый парсинг статей из категории"""
    async def mock_get_page_content(url):
        if "ekonomia" in url and not "art" in url:
            return SAMPLE_CATEGORY_HTML
        return SAMPLE_ARTICLE_HTML
    
    mocker.patch.object(news_parser, '_get_page_content', side_effect=mock_get_page_content)
    
    articles = []
    async for article in news_parser.stream_articles_by_category("ekonomia"):
        articles.append(article)
    
    assert len(articles) == 2
    assert all(isinstance(article, dict) for article in articles)
    assert all("title" in article for article in articles)
    assert all("full_text" in article for article in articles)

@pytest.mark.asyncio
async def test_save_to_json(news_parser, tmp_path):
    """Тест проверяет сохранение статей в JSON"""
    test_data = {
        "category_url": "https://www.rp.pl/ekonomia",
        "articles_found": 1,
        "category_path": "ekonomia",
        "parsed_at": datetime.now().isoformat(),
        "articles": [{
            "title": "Тестовая статья",
            "url": "https://www.rp.pl/ekonomia/art12345",
            "full_text": "Текст статьи",
            "image_url": "https://example.com/image.jpg",
            "author": "Тестовый Автор"
        }]
    }
    
    test_file = news_parser.save_to_json(test_data, "ekonomia")
    
    assert os.path.exists(test_file)
    with open(test_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
        assert saved_data["articles_found"] == 1
        assert saved_data["articles"][0]["title"] == "Тестовая статья"
        assert saved_data["articles"][0]["image_url"] == "https://example.com/image.jpg"
        assert saved_data["articles"][0]["author"] == "Тестовый Автор"

@pytest.mark.asyncio
async def test_parse_by_category_with_images(news_parser, mocker):
    """Тест проверяет, что парсер корректно извлекает все изображения из статей"""
    article_with_images = '''
    <html>
        <h1 class="article--title">Статья с изображениями</h1>
        <div class="blog--image">
            <img src="https://example.com/main.jpg" alt="Главное фото">
        </div>
        <p class="article--media--lead">Описание главного фото</p>
        <p class="image--author">Фотограф Иванов</p>
        
        <div class="article--content">
            <p>Текст статьи</p>
        </div>
    </html>
    '''
    
    category_with_article = '''
    <div class="content--block">
        <a href="/ekonomia/art12345" class="contentLink" data-gtm-trigger="title">Статья</a>
    </div>
    '''
    
    async def mock_get_content(url):
        if "art12345" in url:
            return article_with_images
        return category_with_article
    
    mocker.patch.object(news_parser, '_get_page_content', side_effect=mock_get_content)
    
    result = await news_parser.parse_by_category("ekonomia", limit=1)
    
    assert result["articles_found"] == 1
    article = result["articles"][0]
    assert article["image_url"] == "https://example.com/main.jpg"
    assert article["image_description"] == "Описание главного фото"
    assert article["image_author"] == "Фотограф Иванов"
