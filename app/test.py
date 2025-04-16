import os
from dotenv import load_dotenv
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Update, Message
from aiogram.filters import Command  # Для поддержки фильтров с новыми принципами работы
import logging

load_dotenv()  # Поддержка .env файла для переменных окружения

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен бота
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Публичный адрес вашего сервера
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"  # Путь для Webhook
WEBAPP_HOST = "0.0.0.0"  # Хост для FastAPI
WEBAPP_PORT = int(os.getenv("PORT", 8000))  # Порт для FastAPI

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()  # Диспетчер теперь создаётся без аргументов
router = Router()
# Логирование
logging.basicConfig(level=logging.INFO)


# Регистрация маршрутов
@router.message(Command("start"))
async def start_command(message: Message):
    await message.reply("Привет! Я работаю через Webhook!")

@router.message()
async def echo_handler(message: Message):
    await message.reply(f"Вы сказали: {message.text}")

# Подключаем роутер к диспетчеру
dp.include_router(router)

# Инициализация FastAPI
app = FastAPI()


# Webhook endpoint
@app.post(WEBHOOK_PATH)
async def telegram_webhook(update: dict):  # Тип данных изменён на dict
    """Получает обновления от Telegram"""
    try:
        telegram_update = Update(**update)
        await dp.feed_update(bot, telegram_update)  # Новый метод для обработки обновлений
    except Exception as e:
        logging.error(f"Ошибка обработки Webhook: {e}")
    return {"ok": True}


# Установка Webhook перед запуском приложения
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    logging.info(f"Webhook установлен на {WEBHOOK_URL + WEBHOOK_PATH}")


# Удаление Webhook при завершении работы
@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
    logging.info("Бот остановлен, Webhook удален")


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
