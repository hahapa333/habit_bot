
from fastapi import FastAPI, Depends
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import Update, Message, BotCommand
from aiogram.filters import Command  # Для поддержки фильтров с новыми принципами работы
from app.config import settings
import logging
import bcrypt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import engine, get_db, async_session
from app.models import Base, User, Habit
from aiogram.filters import Command


BOT_TOKEN = settings.BOT_TOKEN  # Токен бота
WEBHOOK_URL = settings.WEBHOOK_URL  # Публичный адрес вашего сервера
WEBHOOK_PATH = settings.WEBHOOK_PATH # Путь для Webhook


# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()  # Диспетчер теперь создаётся без аргументов
router = Router()
# Логирование
logging.basicConfig(level=logging.INFO)


def hash_password(password: str) -> str:
    """Хеширование пароля."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# Регистрация маршрутов
@router.message(Command("start"))
async def start_command(message: Message):
    await message.reply("Привет! Я работаю через Webhook!")

@router.message(Command("echo"))
async def echo_handler(message: Message):
    await message.answer(f"Вы сказали: {message.text}")

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
    # Автоматическое создание схемы БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logging.info("Таблицы созданы в базе данных PostgreSQL.")

    # Настройка команд бота
    await set_bot_commands(bot)

    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    logging.info(f"Webhook установлен на {WEBHOOK_URL + WEBHOOK_PATH}")


@app.get("/")
async def root():
    return {"message": "PostgreSQL подключён успешно."}

# Удаление Webhook при завершении работы
@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
    logging.info("Бот остановлен, Webhook удален")


# Команда для добавления пользователя
@router.message(Command("adduser"))
async def add_user_handler(message: Message):
    async with async_session() as db:
        try:
            username = message.from_user.username or "Без имени"
            telegram_id = message.from_user.id

            # SQL-запрос
            query = select(User).where(User.telegram_id == telegram_id)
            result = await db.execute(query)
            user = result.scalar()

            if user:
                await message.reply("Пользователь уже существует!")
            else:
                new_user = User(
                    username=username,
                    telegram_id=telegram_id,
                    hashed_password="hashed"
                )
                db.add(new_user)
                await db.commit()
                await message.reply(f"Пользователь {username} успешно добавлен!")
        except Exception as e:
            await message.reply("Произошла ошибка!")
            logging.error(f"Ошибка: {e}")


# Команда для получения всех пользователей
@router.message(Command("users"))
async def list_users_handler(message: Message):
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        if not users:
            await message.reply("В базе данных нет пользователей.")
        else:
            user_list = "\n".join([f"{user.id}: {user.username}" for user in users])
            await message.reply(f"Список пользователей:\n{user_list}")


# Обработчик команды /help
@router.message(Command("help"))
async def help_command(message: Message):
    commands = (
        "/start - Начать взаимодействие с ботом\n"
        "/help - Показать список команд\n"
        "/echo - Повторить ваше сообщение\n"
    )
    await message.answer(f"Список доступных команд:\n{commands}")


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Показать список команд"),
        BotCommand(command="adduser", description="Добавить нового пользователя"),
        BotCommand(command="users", description="Показать список пользователей"),
        BotCommand(command="echo", description="Повторить ваше сообщение"),
    ]
    await bot.set_my_commands(commands)
