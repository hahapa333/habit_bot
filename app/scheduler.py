
from sqlalchemy import select

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
    result = await session.execute(select(UserSchedule))
    schedules = result.scalars().all()

    for schedule in schedules:
        try:
            hour, minute = map(int, schedule.time.split(":"))
            job_id = f"reminder_{schedule.id}"  # Уникальный ID задачи

            scheduler.add_job(
                schedule_habit_reminder,
                trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
                args=[schedule.user_id],
                id=job_id,
                replace_existing=True
            )
        except Exception as e:
            print(f"⚠️ Не удалось добавить задачу (ID {schedule.id}): {e}")


async def schedule_habit_reminder(telegram_id: int):
    async with async_session() as session:
        # Получить пользователя по telegram_id
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            logging.warning(f"Пользователь с telegram_id={telegram_id} не найден.")
            return

        # Получить привычки пользователя
        result = await session.execute(select(Habit).where(Habit.user_id == user.id))
        habits = result.scalars().all()

        if not habits:
            logging.info(f"У пользователя {telegram_id} нет привычек.")
            return

        # Отправить напоминание о каждой привычке
        for habit in habits:
            try:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"🔔 Напоминание: не забудьте выполнить привычку «{habit.name_habit}»!"
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке напоминания пользователю {telegram_id}: {e}")




