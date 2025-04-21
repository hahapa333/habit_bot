from pydantic_settings import BaseSettings  # Импорт из нового пакета
from typing import Optional



class Settings(BaseSettings):
    DB_USER: Optional[str] = "postgres"
    DB_PASS: Optional[str] = "postgres"
    DB_HOST: Optional[str] = "db"
    DB_PORT: Optional[int] = 5432  # По умолчанию используется порт PostgreSQL
    DB_NAME: Optional[str] = "habit_db"

    DATABASE_URL: Optional[str] = None
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_PATH: Optional[str] = None

    WEBAPP_HOST: str
    WEBAPP_PORT: Optional[int] = 8000  # Значение по умолчанию

    BOT_TOKEN: str  # Объявляем недостающее поле, соответствующее bot_token в .env-файле
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


    class Config:
        env_file = ".env"


settings = Settings()
