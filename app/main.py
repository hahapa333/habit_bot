import asyncio
from datetime import datetime
import re

import aioschedule
from aiogram.fsm.context import FSMContext
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Update, Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import update, delete
from sqlalchemy.orm import selectinload

from app.FSMContext_class import HabitForm, EditScheduleForm, EditHabitForm
from app.config_env import settings
import logging
import bcrypt

from sqlalchemy.future import select
from app.database import engine, async_session
from app.models import Base, User, Habit, UserSchedule
from aiogram.filters import Command, CommandObject

from app.bot import bot, dp, BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH
# from app.scheduler import scheduler, schedule_habit_reminder, schedule_interval


import collections.abc

from app.scheduler import scheduler, TIMEZONE, schedule_habit_reminder, load_schedules_from_db, reset_habit_completion

collections.Hashable = collections.abc.Hashable

router = Router()
# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def hash_password(password: str) -> str:
    """Хеширование пароля."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# Регистрация маршрутов
@router.message(Command("start"))
async def start_command(message: Message):
    """
    Обработчик команды /start. Регистрирует нового пользователя или сообщает, что он уже существует.

    :param message: Объект сообщения от пользователя.
    """
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

    await message.answer(f"Привет{message.from_user.username}")


@router.message(Command("echo"))
async def echo_handler(message: Message):
    """
    Обработчик команды /echo. Повторяет сообщение пользователя.

    :param message: Объект сообщения от пользователя.
    """
    await message.answer(f"Вы сказали: {message.text}")


# Подключаем роутер к диспетчеру
dp.include_router(router)

# Инициализация FastAPI
app = FastAPI()


# Webhook endpoint
@app.post(WEBHOOK_PATH)
async def telegram_webhook(update: dict):  # Тип данных изменён на dict
    """
    Обработчик Webhook для получения обновлений от Telegram.

    :param update: Обновление в виде словаря.
    :return: Ответ в формате JSON.
    """
    try:
        telegram_update = Update(**update)
        await dp.feed_update(bot, telegram_update)  # Новый метод для обработки обновлений
    except Exception as e:
        logging.error(f"Ошибка обработки Webhook: {e}")
    return {"ok": True}


# Установка Webhook перед запуском приложения

@app.on_event("startup")
async def on_startup():
    """
    Действия, выполняемые при запуске приложения:
    - Создание схемы базы данных.
    - Установка команд бота.
    - Установка Webhook.
    - Запуск планировщика.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Автоматическое создание схемы БД (рекомендуется заменить на Alembic)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Таблицы созданы в базе данных PostgreSQL.")
    except Exception as e:
        logging.error(f"Ошибка при создании таблиц: {e}")
        raise

    # Установка команд бота
    try:
        await set_bot_commands(bot)
    except Exception as e:
        logging.error(f"Ошибка при установке команд бота: {e}")
        raise

    # Установка webhook
    try:
        assert WEBHOOK_URL, "WEBHOOK_URL не задан."
        assert WEBHOOK_PATH, "WEBHOOK_PATH не задан."
        await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH,
                              allowed_updates=["message", "callback_query"])
        logging.info(f"Webhook установлен на {WEBHOOK_URL + WEBHOOK_PATH}")
    except Exception as e:
        logging.error(f"Ошибка при установке Webhook: {e}")
        raise

    # Запуск планировщика (раскомментируйте, если используется)
    try:
        async with async_session() as db:
            await load_schedules_from_db(db)  # ✅ Загрузка всех задач
        scheduler.start()

        # await dp.start_polling(schedule_habit_reminder)
        # asyncio.create_task(scheduler())
    except Exception as e:
        logging.error(f"Ошибка при запуске планировщика: {e}")
        raise


@app.get("/")
async def root():
    """
    Главная страница приложения.

    :return: Сообщение о подключении к PostgreSQL.
    """
    return {"message": "PostgreSQL подключён успешно."}


# Удаление Webhook при завершении работы
@app.on_event("shutdown")
async def on_shutdown():
    """
    Действия, выполняемые при завершении работы приложения:
    - Закрытие сессии бота.
    """
    await bot.session.close()
    logging.info("Бот остановлен, Webhook удален")


# Команда для получения всех пользователей
@router.message(Command("users"))
async def list_users_handler(message: Message):
    """
    Обработчик команды /users. Возвращает список всех пользователей из базы данных.

    :param message: Объект сообщения от пользователя.
    """
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
async def start_add_habit(message: Message, state: FSMContext):
    """
    Обработчик команды /users. Возвращает список всех пользователей из базы данных.

    :param message: Объект сообщения от пользователя.
    """
    await message.answer("Введите название своей привычки:")
    await state.set_state(HabitForm.name)


@router.message(HabitForm.name)
async def get_habit_name(message: Message, state: FSMContext):
    """
    Обрабатывает ввод названия привычки и переходит к шагу ввода времени напоминаний.

    :param message: Объект сообщения от пользователя.
    :param state: Состояние FSM для управления шагами ввода.
    """
    await state.update_data(name=message.text, times=[])
    await message.answer(
        "Введите время напоминания в формате HH:MM. "
        "Можете ввести несколько по одному. Напишите 'Готово', когда закончите:"
    )
    await state.set_state(HabitForm.times)


@router.message(HabitForm.times)
async def get_schedule_times(message: Message, state: FSMContext):
    """
    Обрабатывает ввод времени напоминаний для привычки. Проверяет формат времени и сохраняет данные.

    :param message: Объект сообщения от пользователя.
    :param state: Состояние FSM для управления шагами ввода.
    """
    user_input = message.text.strip()

    # Если пользователь завершает ввод
    if user_input.lower() == "готово":
        data = await state.get_data()
        name = data.get("name")
        times = data.get("times", [])

        if not times:
            await message.answer("Вы не указали ни одного времени.")
            return

        async with async_session() as db:
            try:
                telegram_id = message.from_user.id
                result = await db.execute(select(User).where(User.telegram_id == telegram_id))
                user = result.scalar_one_or_none()

                if not user:
                    await message.answer("Ошибка: пользователь не найден.")
                    return

                new_habit = Habit(user_id=user.id, name_habit=name)
                db.add(new_habit)
                await db.flush()  # Получаем habit.id без коммита

                for time in set(times):  # убираем дубли
                    try:
                        hour, minute = map(int, time.split(":"))
                        assert 0 <= hour < 24 and 0 <= minute < 60
                    except Exception:
                        await message.answer(f"Неверный формат времени: {time}. Пропускаю.")
                        continue

                    new_schedule = UserSchedule(habit_id=new_habit.id, time=time)
                    db.add(new_schedule)
                    await db.flush()  # Получаем schedule.id для job_id

                    job_id = f"reminder_{new_habit.id}_{time.replace(':', '-')}"
                    if not scheduler.get_job(job_id):
                        scheduler.add_job(
                            schedule_habit_reminder,
                            trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
                            args=[user.telegram_id, new_habit.name_habit],
                            id=job_id,
                            replace_existing=True
                        )
                    logging.info(f"Добавлено напоминание: {job_id} для {time}")

                await db.commit()
                await message.answer(
                    f"Привычка «{name}» добавлена с напоминаниями: {', '.join(times)}")

            except Exception as e:
                await message.answer("Ошибка при сохранении.")
                logging.error(f"Ошибка при добавлении привычки: {e}")

        await state.clear()

    # Обработка времени — проверка формата на каждом шаге
    else:
        try:
            hour, minute = map(int, user_input.split(":"))
            assert 0 <= hour < 24 and 0 <= minute < 60
        except:
            await message.answer("Неверный формат. Введите время в формате HH:MM.")
            return

        data = await state.get_data()
        times = data.get("times", [])
        times.append(user_input)
        await state.update_data(times=times)

        await message.answer(f"Время {user_input} добавлено. Введите ещё или напишите 'Готово'.")


# Конец блока создания привычки

# Изменение привычки
@router.callback_query(lambda c: c.data.startswith("edit_schedule:"))
async def start_edit_schedule(callback: CallbackQuery, state: FSMContext):
    habit_id = int(callback.data.split(":")[1])
    await state.set_state(EditScheduleForm.new_times)
    await state.update_data(habit_id=habit_id)
    await callback.message.answer("Введите новое время в формате HH:MM (например, 08:30):")


@router.message(EditScheduleForm.new_times)
async def process_new_schedule_time(message: Message, state: FSMContext):
    async with async_session() as db:
        data = await state.get_data()
        habit_id = data.get("habit_id")
        new_time = message.text.strip()
        telegram_id = message.from_user.id

        # Проверка формата времени
        if not re.match(r"^\d{2}:\d{2}$", new_time):
            await message.answer("Неверный формат времени. Используйте формат HH:MM.")
            return

        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return

        # Проверка существования привычки
        result = await db.execute(
            select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
        )
        habit = result.scalar_one_or_none()

        if not habit:
            await message.answer("Привычка не найдена.")
            await state.clear()
            return
        hour, minute = map(int, new_time.split(":"))

        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Неверный диапазон времени.")
        # Удалим старое расписание и добавим новое
        await db.execute(delete(UserSchedule).where(UserSchedule.habit_id == habit.id))
        new_schedule = UserSchedule(habit_id=habit.id, time=new_time)
        db.add(new_schedule)
        await db.commit()
        # Планируем задачу
        job_id = f"reminder_habit_{habit.id}"

        scheduler.add_job(
            schedule_habit_reminder,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
            args=[user.telegram_id, habit.name_habit],
            id=job_id,
            replace_existing=True
        )
        await message.answer(f"Расписание для привычки обновлено на {new_time} ⏰")
    await state.clear()


# Конец блока изменения привычки


# Изменение названия привычки
@router.message(EditHabitForm.new_habit)
async def process_new_habit_name(message: Message, state: FSMContext):
    async with async_session() as db:
        data = await state.get_data()
        habit_id = data.get("habit_id")
        new_name = message.text.strip()
        telegram_id = message.from_user.id

        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return

        result = await db.execute(
            select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
        )
        habit = result.scalar_one_or_none()

        if not habit:
            await message.answer("Привычка не найдена.")
            await state.clear()
            return

        habit.name_habit = new_name
        await db.commit()
        await message.answer(f"Название привычки обновлено на: {new_name}")

    await state.clear()


@router.callback_query(lambda c: c.data.startswith("edit_habit:"))
async def handle_edit_habit_callback(callback_query: CallbackQuery, state: FSMContext):
    habit_id = int(callback_query.data.split(":")[1])

    await state.set_state(EditHabitForm.new_habit)
    await state.update_data(habit_id=habit_id)

    await callback_query.message.answer("Введите новое название привычки:")
    await callback_query.answer()  # Закрыть "часики"


# Конец блока изменения названия привычки

# Команда для получения всех привычек пользователя
@router.message(Command("habit_list"))
async def list_habits(message: Message):
    async with async_session() as session:
        telegram_id = message.from_user.id

        result = await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(
                selectinload(User.habits).selectinload(Habit.schedules)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ Пользователь не найден.")
            return

        if not user.habits:
            await message.answer("ℹ️ У вас пока нет привычек.")
            return

        for habit in user.habits:
            schedule_times = [s.time for s in habit.schedules]
            times_text = ", ".join(schedule_times) if schedule_times else "⏰ Нет напоминаний"
            status = "✅ Выполнено" if habit.is_completed else "❌ Не выполнено"

            text = f"{habit.id}. {habit.name_habit} — {status}\n🕒 Напоминания: {times_text}"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Выполнил", callback_data=f"complete_habit:{habit.id}"),
                    InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_habit:{habit.id}"),
                    InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_habit:{habit.id}"),
                    InlineKeyboardButton(text="🕒 Изменить расписание", callback_data=f"edit_schedule:{habit.id}")

                ]
            ])

            await message.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith("delete_habit:"))
async def handle_delete_habit(callback_query: CallbackQuery):
    habit_id = int(callback_query.data.split(":")[1])
    telegram_id = callback_query.from_user.id

    async with async_session() as db:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            await callback_query.message.answer("Ошибка: пользователь не найден.")
            return

        result = await db.execute(
            select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
        )
        habit = result.scalar_one_or_none()

        if not habit:
            await callback_query.message.answer("Привычка не найдена или уже удалена.")
            return

        await db.delete(habit)
        await db.commit()

        await callback_query.message.edit_text(f"Привычка '{habit.name_habit}' удалена.")


@router.callback_query(lambda c: c.data.startswith("complete_habit:"))
async def complete_habit(callback_query: CallbackQuery):
    habit_id = int(callback_query.data.split(":")[1])
    telegram_id = callback_query.from_user.id

    async with async_session() as db:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        scheduler.add_job(
            reset_habit_completion,
            trigger=CronTrigger(hour=0, minute=0, timezone=TIMEZONE),
            id="reset_completion_daily",
            replace_existing=True
        )
        if not user:
            await callback_query.message.answer("Ошибка: пользователь не найден.")
            return

        result = await db.execute(
            select(Habit).where(Habit.id == habit_id, Habit.user_id == user.id)
        )
        habit = result.scalar_one_or_none()

        if not habit:
            await callback_query.message.answer("Привычка не найдена.")
            return

        habit.is_completed = True
        await db.commit()

        await callback_query.message.edit_text(f"Привычка «{habit.name_habit}» отмечена как выполненная ✅")


@router.message(Command("setdays"))
async def set_habit_days(message: Message):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("Используйте формат: /setdays 30")
        return

    days = int(args[1])
    if not (1 <= days <= 100):
        await message.answer("Число должно быть от 1 до 100.")
        return

    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Пользователь не найден.")
            return

        await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(habit_days=days)
        )
        await session.commit()

        await message.answer(f"Срок закрепления привычек установлен на {days} дней ✅")


# Обработчик команды /help
@router.message(Command("help"))
async def help_command(message: Message):
    commands = (
        "/start - Начать взаимодействие с ботом\n"
        "/help - Показать список команд\n"
        "/echo - Повторить ваше сообщение\n"
        "/addhabit - Добавить новую привычку\n"
        "/users - Показать список пользователей\n"
        "/habit_list - Показать список привычек\n"
        "/setdays - Установить срок закрепления привычек\n"
    )
    await message.answer(f"Список доступных команд:\n{commands}")


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Показать список команд"),
        BotCommand(command="addhabit", description="Добавить новую привычку"),
        BotCommand(command="users", description="Показать список пользователей"),
        BotCommand(command="habit_list", description="Показать список привычек"),
        BotCommand(command="setdays", description="Установить срок закрепления привычек"),
        BotCommand(command="echo", description="Повторить ваше сообщение"),
    ]
    await bot.set_my_commands(commands)
