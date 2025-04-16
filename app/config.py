from pydantic_settings import BaseSettings  # Импорт из нового пакета



class Settings(BaseSettings):
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DATABASE_URL: str = None
    WEBHOOK_URL: str
    WEBHOOK_PATH: str
    WEBAPP_HOST: str
    WEBAPP_PORT: int
    BOT_TOKEN: str  # Объявляем недостающее поле, соответствующее bot_token в .env-файле
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


    class Config:
        env_file = ".env"


settings = Settings()
