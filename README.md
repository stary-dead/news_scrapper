# 📰 RP News Aggregator

## 📌 Project Overview

**RP News Aggregator** is a microservices-based system for scraping, analyzing, and delivering news from the Polish news website [rp.pl](https://www.rp.pl). It is designed to demonstrate modern backend architecture using Django, Celery, RabbitMQ, and Kubernetes.

## 🚀 Features

- Scrape news articles from [rp.pl]
- Store data in PostgreSQL
- RESTful API to access and search news
- Telegram bot for daily headlines and keyword search
- Scalable deployment with Docker & Kubernetes
- Basic NLP: keyword extraction, category tagging

## 🛠️ Tech Stack

- Python 3.10
- Django + Django REST Framework
- Celery + RabbitMQ
- PostgreSQL
- Aiogram (Telegram Bot)
- Docker + Docker Compose
- Kubernetes (with Helm optionally)
- BeautifulSoup + Aiohttp

---

## 📂 Project Structure

rp-news-aggregator/
├── parser/ # Async news scraper (Celery worker)
├── django_app/ # Django project with REST API
├── telegram_bot/ # Aiogram-based Telegram bot
├── scripts/ # Helper and init scripts
├── k8s/ # Kubernetes manifests
├── docker-compose.yml # Local container orchestration
├── requirements.txt # Python dependencies
└── README.md # This file


---

## 📈 Development Roadmap

### ✅ Phase 1: Research & Parsing Prototype
- Analyze the rp.pl website structure
- Build a simple asynchronous parser using `aiohttp` + `BeautifulSoup`
- Output titles, URLs, timestamps, descriptions

### 🛠️ Phase 2: Celery-Based Parsing Microservice
- Integrate the parser as a Celery task
- Use RabbitMQ as the broker
- Periodically fetch news and store in PostgreSQL

### 🌐 Phase 3: API and Admin Panel
- Create Django models for news articles
- Provide API endpoints (list, detail, search by keyword/date/category)
- Add Django admin interface

### 🤖 Phase 4: Telegram Bot
- Build a Telegram bot using Aiogram
- Allow users to:
  - View latest news
  - Search by keywords
  - Subscribe to daily digests

### 🐳 Phase 5: Containerization and Kubernetes
- Dockerize all services
- Provide `docker-compose.yml` for local dev
- Kubernetes manifests for production (or Helm charts)
- Ingress + optional TLS termination

### (Optional) 📊 Phase 6: NLP & Web Interface
- Keyword extraction (e.g., `yake`, `spaCy`)
- Sentiment analysis
- Minimal frontend with search and filter

---

## 🧪 Getting Started (Local)

```bash
git clone https://github.com/stary-dead/rp-news-aggregator.git
cd rp-news-aggregator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
docker-compose up --build
