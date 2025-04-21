from fastapi import FastAPI
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Update, Message, BotCommand
from app.config_env import settings
import logging
import bcrypt

from sqlalchemy.future import select
from app.database import engine, async_session
from app.models import Base, User, Habit
from aiogram.filters import Command, CommandObject


BOT_TOKEN = settings.BOT_TOKEN  # Токен бота
WEBHOOK_URL = settings.WEBHOOK_URL  # Публичный адрес вашего сервера
WEBHOOK_PATH = settings.WEBHOOK_PATH  # Путь для Webhook

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
    # Для тестирования в env.py временно добавьте:
    print(Base.metadata.tables.keys())

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
            hashed_password = hash_password("hashed")

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
                    hashed_password=hashed_password
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


# Добавить новую привычку
@router.message(Command("addhabit"))
async def add_habit(message: Message):
    # Попросим ввести название привычки
    await message.answer("Введите название своей привычки:")

    @router.message()
    async def save_habits(message: Message):
        async with async_session() as db:
            try:
                name_habit = message.text
                telegram_id = message.from_user.id

                # SQL-запрос
                query = select(User).where(User.telegram_id == telegram_id)
                result = await db.execute(query)
                user = result.scalar()

                if user:
                    new_habit = Habit(user_id=user.id, name_habit=name_habit)
                    db.add(new_habit)
                    await db.commit()
                    await message.answer(f"Привычка '{name_habit}' успешно добавлена!")

                else:
                    await message.answer("Ошибка: привычка не добавлена.")

            except Exception as e:
                await message.reply("Произошла ошибка!")
                logging.error(f"Ошибка: {e}")


# Команда для получения всех привычек пользователя
@router.message(Command("habit_list"))
async def list_habits(message: Message):
    async with async_session() as db:
        telegram_id = message.from_user.id
        # SQL-запрос
        query = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(query)
        user = result.scalar()

    if user:
        query = select(Habit).filter(Habit.user_id == user.id)
        habits = await db.execute(query)

        habits = habits.scalars().all()

        if habits:
            text = "\n".join(
                [f"{habit.id}. {habit.name_habit}"
                 for habit in habits]
            )
            await message.answer(f"Ваши привычки:\n{text}")
        else:
            await message.answer("У вас пока нет привычек.")
    else:
        await message.answer("Ошибка: пользователь не найден.")


from aiogram.filters.command import CommandObject


@router.message(Command("edit_habit"))
async def edit_habit(message: Message, command: CommandObject):
    """
    Обработчик команды для редактирования названия привычки.
    Формат команды: /edit_habit <id привычки> <новое название>
    """
    async with async_session() as db:
        telegram_id = message.from_user.id

        # Проверяем, что команда содержит ID и новое название
        if not command.args:
            await message.answer("Использование: /edit_habit <id привычки> <новое название>")
            return

        args = command.args.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Использование: /edit_habit <id привычки> <новое название>")
            return

        try:
            habit_id = int(args[0])
            new_name = args[1].strip()
        except ValueError:
            await message.answer("ID привычки должен быть числом.")
            return

        # Получаем пользователя по Telegram ID
        query = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(query)
        user = result.scalar()

        if not user:
            await message.answer("Ошибка: пользователь не найден.")
            return

        # Получаем привычку по ID и проверяем принадлежность пользователю
        query = select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
        result = await db.execute(query)
        habit = result.scalar()

        if not habit:
            await message.answer("Привычка с таким ID не найдена или не принадлежит вам.")
            return

        # Редактируем привычку
        habit.name_habit = new_name
        await db.commit()

        await message.answer(f"Привычка успешно обновлена: {habit.id}. {habit.name_habit}")


@router.message(Command("delete_habit"))
async def delete_habit(message: Message, command: CommandObject):
    """
    Обработчик команды для удаления привычки.
    Формат команды: /delete_habit <id привычки>
    """
    async with async_session() as db:
        telegram_id = message.from_user.id

        # Проверяем, что команда содержит ID привычки
        if not command.args:
            await message.answer("Использование: /delete_habit <id привычки>")
            return

        try:
            habit_id = int(command.args.strip())
        except ValueError:
            await message.answer("ID привычки должен быть числом.")
            return

        # Получаем пользователя по Telegram ID
        query = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(query)
        user = result.scalar()

        if not user:
            await message.answer("Ошибка: пользователь не найден.")
            return

        # Проверяем, существует ли привычка с указанным ID и принадлежит ли она пользователю
        query = select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
        result = await db.execute(query)
        habit = result.scalar()

        if not habit:
            await message.answer("Привычка с таким ID не найдена или не принадлежит вам.")
            return

        # Удаляем привычку
        await db.delete(habit)
        await db.commit()

        await message.answer(f"Привычка {habit_id} успешно удалена.")


@router.message(Command("set_habit_status"))
async def set_habit_status(message: Message, command: CommandObject):
    """
    Обработчик команды для фиксации выполнения привычки.
    Формат команды: /set_habit_status <id привычки> <выполнил/не выполнил>
    """
    async with async_session() as db:
        telegram_id = message.from_user.id

        # Проверяем аргументы команды
        if not command.args:
            await message.answer("Использование: /set_habit_status <id привычки> <выполнил/не выполнил>")
            return

        args = command.args.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Использование: /set_habit_status <id привычки> <выполнил/не выполнил>")
            return

        try:
            habit_id = int(args[0])
            status_text = args[1].strip().lower()
        except ValueError:
            await message.answer("ID привычки должен быть числом.")
            return

        # Определяем статус выполнения
        if status_text == "выполнил":
            is_completed = True
        elif status_text == "не выполнил":
            is_completed = False
        else:
            await message.answer("Статус должен быть либо 'выполнил', либо 'не выполнил'.")
            return

        # Проверяем, существует ли пользователь
        query = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(query)
        user = result.scalar()

        if not user:
            await message.answer("Ошибка: пользователь не найден.")
            return

        # Проверяем, существует ли привычка и принадлежит ли она пользователю
        query = select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
        result = await db.execute(query)
        habit = result.scalar()

        if not habit:
            await message.answer("Привычка с таким ID не найдена или не принадлежит вам.")
            return

        # Фиксируем выполнение
        habit.is_completed = is_completed
        await db.commit()

        status_message = "выполнена" if is_completed else "не выполнена"
        await message.answer(f"Привычка {habit.id} успешно отмечена как {status_message}.")

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
        BotCommand(command="addhabit", description="Добавить новую привычку"),
        BotCommand(command="users", description="Показать список пользователей"),
        BotCommand(command="habit_list", description="Показать список привычек"),
        BotCommand(command="edit_habit", description="Редактировать привычку"),
        BotCommand(command="delete_habit", description="Удалить привычку"),
        BotCommand(command="set_habit_status", description="выполнил не выполнил"),
        BotCommand(command="echo", description="Повторить ваше сообщение"),
    ]
    await bot.set_my_commands(commands)
