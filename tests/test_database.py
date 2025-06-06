"""Unit tests for database service"""
import pytest
import asyncio
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from db_service.database import DatabaseService
from db_service.models import Base, Article

@pytest.fixture(scope="session")
def db_engine(setup_test_db):
    """Create database engine"""
    engine = create_engine(setup_test_db)
    Base.metadata.create_all(engine)
    yield engine
    # Drop all tables after all tests
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(autouse=True)
def clean_tables(db_engine):
    """Clean tables before each test"""
    # Start transaction
    connection = db_engine.connect()
    transaction = connection.begin()
    
    try:
        # Delete all records from articles table
        connection.execute(text("DELETE FROM articles"))
        connection.execute(text("ALTER SEQUENCE articles_id_seq RESTART WITH 1"))
        transaction.commit()
    except Exception as e:
        transaction.rollback()
        raise
    finally:
        connection.close()

@pytest.fixture
def session(db_engine):
    """Create new session for each test"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def db_service(setup_test_db):
    """Create database service instance"""
    return DatabaseService(setup_test_db)

@pytest.fixture
def sample_article_data():
    """Sample article data for testing"""
    return {
        'title': 'Test Article',
        'url': 'https://example.com/test-article',
        'content': 'Test content',
        'publication_date': datetime.now(UTC).isoformat(),
        'image_url': 'https://example.com/image.jpg',
        'author': 'Test Author'
    }

@pytest.mark.asyncio
async def test_init_db(db_service, db_engine):
    """Test database initialization"""
    # Drop all tables first
    Base.metadata.drop_all(db_engine)
    
    # Initialize database
    db_service.init_db()
      # Check if tables were created
    from sqlalchemy import inspect
    inspector = inspect(db_engine)
    tables = inspector.get_table_names()
    
    assert 'articles' in tables

@pytest.mark.asyncio
async def test_save_article_success(db_service, sample_article_data, session):
    """Test successful article saving"""
    result = await db_service.save_article(sample_article_data, "test_category")
    
    assert result is True
    
    # Verify article was saved
    article = session.query(Article).first()
    assert article is not None
    assert article.title == 'Test Article'
    assert article.url == 'https://example.com/test-article'
    assert article.category_name == 'test_category'
    assert article.processed is False

@pytest.mark.asyncio
async def test_save_duplicate_article(db_service, sample_article_data, session):
    """Test saving duplicate article (same URL)"""
    # Save first article
    await db_service.save_article(sample_article_data, "test_category")
    
    # Try to save the same article again
    result = await db_service.save_article(sample_article_data, "test_category")
    
    assert result is False
    
    # Verify only one article exists
    count = session.query(Article).count()
    assert count == 1

@pytest.mark.asyncio
async def test_get_unprocessed_articles(db_service, session):
    """Test retrieving unprocessed articles"""
    # Create test articles
    articles = [
        Article(
            title=f'Article {i}',
            url=f'https://example.com/article-{i}',
            content=f'Content {i}',
            category_name='test_category',
            publication_date=datetime.now(UTC),
            processed=False
        ) for i in range(3)
    ]
    
    # Add one processed article
    processed_article = Article(
        title='Processed Article',
        url='https://example.com/processed',
        content='Processed content',
        category_name='test_category',
        publication_date=datetime.now(UTC),
        processed=True
    )
    
    # Add articles to session and commit
    for article in articles + [processed_article]:
        session.add(article)
        session.flush()
    session.commit()
    
    # Get unprocessed articles
    unprocessed = await db_service.get_unprocessed_articles()
    
    assert len(unprocessed) == 3
    assert all(not article['processed'] for article in unprocessed)
    assert all(article['title'].startswith('Article') for article in unprocessed)

@pytest.mark.asyncio
async def test_get_unprocessed_articles_with_limit(db_service, session):
    """Test retrieving unprocessed articles with limit"""
    # Create 5 test articles
    articles = [
        Article(
            title=f'Article {i}',
            url=f'https://example.com/article-{i}',
            content=f'Content {i}',
            category_name='test_category',
            publication_date=datetime.now(UTC),
            processed=False
        ) for i in range(5)
    ]
    
    # Add articles to session and commit
    for article in articles:
        session.add(article)
    session.commit()
    
    # Get limited number of unprocessed articles
    unprocessed = await db_service.get_unprocessed_articles(limit=2)
    assert len(unprocessed) == 2

@pytest.mark.asyncio
async def test_mark_article_as_processed(db_service, session):
    """Test marking article as processed"""
    # Create test article
    article = Article(
        title='Test Article',
        url='https://example.com/test',
        content='Test content',
        category_name='test_category',
        publication_date=datetime.now(UTC),
        processed=False
    )
    session.add(article)
    session.commit()
    article_id = article.id
    
    # Mark article as processed
    await db_service.mark_article_as_processed(article_id)
    
    # Check in same session
    session.refresh(article)
    assert article.processed is True

@pytest.mark.asyncio
async def test_mark_nonexistent_article(db_service):
    """Test marking non-existent article as processed"""
    # Should not raise an error
    await db_service.mark_article_as_processed(999)

@pytest.mark.asyncio
async def test_article_creation_with_missing_fields(db_service, session):
    """Test article creation with minimal required fields"""
    minimal_article = {
        'title': 'Minimal Article',
        'url': 'https://example.com/minimal',
        'publication_date': datetime.now(UTC).isoformat()
    }
    
    result = await db_service.save_article(minimal_article, "test_category")
    assert result is True
    
    # Query in the same session
    article = session.query(Article).first()
    assert article is not None
    assert article.title == 'Minimal Article'
    assert article.content is None
    assert article.image_url is None
    assert article.author is None

@pytest.mark.asyncio
async def test_get_unprocessed_articles_order(db_service, session):
    """Test that unprocessed articles are returned in correct order (by publication date)"""
    # Create articles with different dates
    dates = [
        datetime(2025, 1, 1),
        datetime(2025, 1, 2),
        datetime(2025, 1, 3)
    ]
    
    for i, date in enumerate(dates):
        article = Article(
            title=f'Article {i}',
            url=f'https://example.com/article-{i}',
            content=f'Content {i}',
            category_name='test_category',
            publication_date=date,
            processed=False
        )
        session.add(article)
        session.flush()
    
    session.commit()
    
    # Get unprocessed articles
    unprocessed = await db_service.get_unprocessed_articles()
    
    # Verify order
    assert len(unprocessed) == 3
    for i in range(len(unprocessed) - 1):
        curr_date = datetime.fromisoformat(unprocessed[i]['publication_date'])
        next_date = datetime.fromisoformat(unprocessed[i + 1]['publication_date'])
        assert curr_date <= next_date

@pytest.mark.asyncio
async def test_save_article_invalid_date(db_service, session):
    """Test saving article with invalid date format"""
    invalid_article = {
        'title': 'Invalid Date Article',
        'url': 'https://example.com/invalid-date',
        'publication_date': 'invalid-date',
        'content': 'Test content'
    }
    
    result = await db_service.save_article(invalid_article, "test_category")
    assert result is False
    
    # Verify no article was saved
    count = session.query(Article).count()
    assert count == 0

@pytest.mark.asyncio
async def test_save_article_missing_required_fields(db_service, session):
    """Test saving article with missing required fields"""
    incomplete_article = {
        'title': 'Incomplete Article'
        # Отсутствуют обязательные поля url и publication_date
    }
    
    result = await db_service.save_article(incomplete_article, "test_category")
    assert result is False
    
    # Verify no article was saved
    count = session.query(Article).count()
    assert count == 0

@pytest.mark.asyncio
async def test_get_unprocessed_articles_empty_db(db_service, session):
    """Test getting unprocessed articles from empty database"""
    unprocessed = await db_service.get_unprocessed_articles()
    assert len(unprocessed) == 0

@pytest.mark.asyncio
async def test_get_unprocessed_articles_all_processed(db_service, session):
    """Test getting unprocessed articles when all articles are processed"""
    # Create processed articles
    articles = [
        Article(
            title=f'Processed Article {i}',
            url=f'https://example.com/processed-{i}',
            content=f'Content {i}',
            category_name='test_category',
            publication_date=datetime.now(UTC),
            processed=True
        ) for i in range(3)
    ]
    
    for article in articles:
        session.add(article)
        session.flush()
    session.commit()
    
    # Try to get unprocessed articles
    unprocessed = await db_service.get_unprocessed_articles()
    assert len(unprocessed) == 0

@pytest.mark.asyncio
async def test_long_content_article(db_service, session):
    """Test saving article with very long content"""
    long_content = 'A' * 10000  # 10K characters
    article_data = {
        'title': 'Long Content Article',
        'url': 'https://example.com/long-content',
        'content': long_content,
        'publication_date': datetime.now(UTC).isoformat()
    }
    
    result = await db_service.save_article(article_data, "test_category")
    assert result is True
    
    # Verify article was saved with full content
    saved_article = session.query(Article).first()
    assert saved_article is not None
    assert len(saved_article.content) == 10000

@pytest.mark.asyncio
async def test_unicode_content_article(db_service, session):
    """Test saving article with unicode content"""
    unicode_content = 'Тестовая статья с Unicode символами: 🚀 📰 💻 🌍'
    article_data = {
        'title': 'Unicode Article',
        'url': 'https://example.com/unicode',
        'content': unicode_content,
        'publication_date': datetime.now(UTC).isoformat()
    }
    
    result = await db_service.save_article(article_data, "test_category")
    assert result is True
    
    # Verify article was saved with correct unicode content
    saved_article = session.query(Article).first()
    assert saved_article is not None
    assert saved_article.content == unicode_content
