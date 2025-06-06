"""Unit tests for Telegram bot functionality"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from telegram_bot.bot import process_article_message, send_telegram_message

@pytest.fixture
def complete_article():
    """Fixture with complete article data"""
    return {
        "article": {
            "title": "Test Article",
            "subtitle": "Test Subtitle",
            "url": "https://example.com/article",
            "author": "Test Author",
            "publication_date": "2025-06-06",
            "image_url": "https://example.com/image.jpg"
        },
        "category_name": "Test Category"
    }

@pytest.fixture
def minimal_article():
    """Fixture with minimal article data"""
    return {
        "article": {
            "title": "Test Article",
            "url": "https://example.com/article"
        },
        "category_name": "Test Category"
    }

@pytest.mark.asyncio
async def test_send_telegram_message_with_photo():
    """Test sending message with photo"""
    mock_bot = AsyncMock()
    mock_bot.send_photo = AsyncMock(return_value=True)
    
    with patch('telegram_bot.bot.bot', mock_bot):
        success = await send_telegram_message(
            chat_id=-1002745773579,
            message_text="Test message",
            photo_url="https://example.com/image.jpg"
        )
        
        assert success is True
        mock_bot.send_photo.assert_called_once_with(
            chat_id=-1002745773579,
            photo="https://example.com/image.jpg",
            caption="Test message",
            parse_mode="Markdown"
        )

@pytest.mark.asyncio
async def test_send_telegram_message_without_photo():
    """Test sending message without photo"""
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock(return_value=True)
    
    with patch('telegram_bot.bot.bot', mock_bot):
        success = await send_telegram_message(
            chat_id=-1002745773579,
            message_text="Test message"
        )
        
        assert success is True
        mock_bot.send_message.assert_called_once_with(
            chat_id=-1002745773579,
            text="Test message",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

@pytest.mark.asyncio
async def test_process_complete_article(complete_article):
    """Test processing article with all fields present"""
    mock_send = AsyncMock(return_value=True)
    
    with patch('telegram_bot.bot.send_telegram_message', mock_send):
        await process_article_message(complete_article)
        
        expected_text = (
            "📰 *Test Article*\n\n"
            "📁 Test Category\n"
            "🔍 Test Subtitle\n\n"
            "📅 2025-06-06\n"
            "✍️ Test Author\n\n"
            "🔗 [Czytaj więcej](https://example.com/article)"
        )
        
        mock_send.assert_called_once_with(
            chat_id=-1002745773579,
            message_text=expected_text,
            photo_url="https://example.com/image.jpg"
        )

@pytest.mark.asyncio
async def test_process_minimal_article(minimal_article):
    """Test processing article with minimal fields"""
    mock_send = AsyncMock(return_value=True)
    
    with patch('telegram_bot.bot.send_telegram_message', mock_send):
        await process_article_message(minimal_article)
        
        expected_text = (
            "📰 *Test Article*\n\n"
            "📁 Test Category\n"
            "🔍 \n\n"
            "📅 Data nie podana\n"
            "✍️ Autor nie podany\n\n"
            "🔗 [Czytaj więcej](https://example.com/article)"
        )
        
        mock_send.assert_called_once_with(
            chat_id=-1002745773579,
            message_text=expected_text,
            photo_url=None
        )

@pytest.mark.asyncio
async def test_process_article_with_empty_message():
    """Test processing empty message"""
    mock_send = AsyncMock(return_value=True)
    
    with patch('telegram_bot.bot.send_telegram_message', mock_send):
        await process_article_message({})
        mock_send.assert_not_called()

@pytest.mark.asyncio
async def test_send_telegram_message_with_retries():
    """Test retrying message send on failure"""
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock(side_effect=[Exception(), Exception(), True])
    
    with patch('telegram_bot.bot.bot', mock_bot):
        success = await send_telegram_message(
            chat_id=-1002745773579,
            message_text="Test message"
        )
        
        assert success is True
        assert mock_bot.send_message.call_count == 3
