from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config_env import settings
import logging

# Создаем асинхронный движок SQLAlchemy для PostgreSQL
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Создаем асинхронную фабрику сессий
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Функция для запроса сессии
async def get_db():
    try:
        async with async_session() as session:
            yield session
    except Exception as e:
        # Логируем ошибки базы данных
        logging.error(f"Ошибка при открытии сессии БД: {e}")
        raise

