import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database, drop_database

TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/test_news_db"
MAIN_DB_URL = "postgresql://postgres:postgres@localhost:5432/postgres"

@pytest.fixture(scope="session")
def db_url():
    """Фикстура, возвращающая URL тестовой базы данных"""
    return TEST_DB_URL

@pytest.fixture(scope="session")
def setup_test_db():
    """
    Фикстура для создания и удаления тестовой базы данных.
    Создает базу данных перед тестами и удаляет после выполнения всех тестов.
    """
    # Подключаемся к основной базе данных postgres
    engine = create_engine(MAIN_DB_URL)
    
    # Если тестовая база существует, удаляем её
    if database_exists(TEST_DB_URL):
        drop_database(TEST_DB_URL)
    
    # Создаем новую тестовую базу
    create_database(TEST_DB_URL)
    
    yield TEST_DB_URL  # Возвращаем URL тестовой базы для использования в тестах
    
    # После выполнения всех тестов удаляем тестовую базу
    if database_exists(TEST_DB_URL):
        drop_database(TEST_DB_URL)
