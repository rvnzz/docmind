from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
import os
from typing import Generator

from .models import Base

# Получаем URL из переменных окружения
# Используем отдельную БД для документов (можно ту же что и для векторов)
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("PGVECTOR_CONNECTION"))

# Создаем engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,  # Включить для дебага
)

# Создаем сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Контекстный менеджер для сессии БД"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Создает таблицы"""
    Base.metadata.create_all(bind=engine)

def drop_db():
    """Удаляет таблицы (только для тестов)"""
    Base.metadata.drop_all(bind=engine)

def get_db_session() -> Session:
    """Получает сессию БД (для FastAPI Dependency)"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise