# Polish News Scraper 🗞️

A microservices-based system for scraping, processing, and delivering news articles from rp.pl to Telegram channels.

## 🚀 Features

- Asynchronous web scraping with rate limiting and error handling
- Article parsing with support for:
  - Titles, subtitles, and content 
  - Publication dates
  - Authors and image credits
  - Article categories and breadcrumbs
- Message queue integration with RabbitMQ
- PostgreSQL storage for articles
- Telegram bot for news delivery
- Containerized deployment with Docker Compose
- Comprehensive test coverage

## 🏗️ Architecture

The system consists of three main microservices:

1. **Parser Service** (`parser/`)
   - Scrapes articles from rp.pl
   - Extracts article content and metadata
   - Publishes to RabbitMQ queue

2. **Database Service** (`db_service/`)
   - Stores articles in PostgreSQL
   - Handles article deduplication
   - Manages article processing status

3. **Telegram Bot** (`telegram_bot/`)
   - Formats articles for Telegram
   - Delivers news to channels
   - Handles message retries

## 📋 Prerequisites

- Python 3.10+
- Docker and Docker Compose
- PostgreSQL 15
- RabbitMQ 3.x

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/polish-news-scraper.git
cd polish-news-scraper
```

2. Create and configure `.env` file:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Build and start services:
```bash
docker-compose up -d
```

## 🧪 Running Tests

Use the provided PowerShell script to run tests:

```bash
./run_tests.ps1
```

This will:
- Start required Docker containers
- Set up test database
- Run pytest with all test suites

## 📝 Environment Variables

Required environment variables in `.env`:

```ini
# Bot configuration
BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id

# Database
POSTGRES_DB=news_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# RabbitMQ
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest
```

## 🔄 Service Workflow

1. Parser service periodically checks rp.pl categories
2. New articles are published to RabbitMQ
3. Database service stores unique articles
4. Telegram bot formats and delivers articles to channel
5. Articles are marked as processed after delivery

## 🛡️ Error Handling

- Retry mechanisms for network requests
- Message queue persistence
- Duplicate article detection
- Rate limiting for API requests
- Comprehensive error logging

## 🧪 Test Coverage

Includes tests for:
- Article parsing and extraction
- Database operations
- Message queue handling
- Telegram message formatting
- Error scenarios

## 📦 Project Structure

```
.
├── parser/              # News scraping service
├── db_service/          # Database operations
├── telegram_bot/        # Telegram delivery
├── tests/              # Test suites
├── docker-compose.yml  # Service orchestration
└── requirements.txt    # Python dependencies
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to your branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.