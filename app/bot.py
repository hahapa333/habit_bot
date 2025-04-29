from aiogram import Dispatcher, Bot

from app.config_env import settings

BOT_TOKEN = settings.BOT_TOKEN  # Токен бота
WEBHOOK_URL = settings.WEBHOOK_URL  # Публичный адрес вашего сервера
WEBHOOK_PATH = settings.WEBHOOK_PATH  # Путь для Webhook

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()  # Диспетчер теперь создаётся без аргументов