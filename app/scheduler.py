
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.bot import bot, dp, BOT_TOKEN
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
import logging

from app.database import async_session
from app.models import Habit, User, UserSchedule

API_TOKEN = BOT_TOKEN  # Замените на ваш токен
TIMEZONE = ZoneInfo("Europe/Moscow")

# ---------- Хранилище расписания ----------
SCHEDULE_FILE = "schedule.json"
scheduled_times = {}  # user_id: "HH:MM"
scheduler = AsyncIOScheduler()

async def load_schedules_from_db(session):
    result = await session.execute(
        select(UserSchedule).options(selectinload(UserSchedule.habit).selectinload(Habit.user))
    )
    schedules = result.scalars().all()

    for schedule in schedules:
        try:
            hour, minute = map(int, schedule.time.split(":"))
            job_id = f"reminder_{schedule.id}"

            # Получаем Telegram ID через habit → user
            telegram_id = schedule.habit.user.telegram_id

            scheduler.add_job(
                schedule_habit_reminder,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
                args=[telegram_id, schedule.habit.name_habit],
                id=job_id,
                replace_existing=True
            )
        except Exception as e:
            print(f"⚠️ Не удалось добавить задачу (ID {schedule.id}): {e}")




async def schedule_habit_reminder(telegram_id: int, habit_name: str):
    """Отправляет напоминания для всех привычек пользователя по заданному Telegram ID"""
    async with async_session() as session:
        try:
            # Получаем пользователя вместе с привычками и расписанием
            result = await session.execute(
                select(User)
                .where(User.telegram_id == telegram_id)
                .options(selectinload(User.habits).selectinload(Habit.schedules))
            )
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"Пользователь с Telegram ID {telegram_id} не найден")

            for habit in user.habits:
                # Опционально: проверка, есть ли для привычки расписание
                if habit.schedules:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=f"Напоминание: не забудьте выполнить привычку «{habit_name}» 🕒"
                    )
        except Exception as e:
            logging.error(f"Ошибка при отправке напоминания для пользователя {telegram_id}: {e}")





