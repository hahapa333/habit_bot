import asyncio

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.bot import bot, dp, BOT_TOKEN
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
import logging
from datetime import datetime, timedelta
from app.database import async_session
from app.models import Habit, User, UserSchedule

API_TOKEN = BOT_TOKEN  # Замените на ваш токен
TIMEZONE = ZoneInfo("Europe/Moscow")

scheduled_times = {}  # user_id: "HH:MM"
scheduler = AsyncIOScheduler()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def create_job(telegram_id: int, habit_name: str):
    def job():
        asyncio.create_task(schedule_habit_reminder(telegram_id, habit_name))

    return job


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
            logging.info("Загрузка расписания для пользователя: %s", telegram_id)

            scheduler.add_job(
                create_job(telegram_id, schedule.habit.name_habit),
                trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
                id=job_id,
                replace_existing=True
            )
            logging.info("✅ Задача добавлена в расписание: %s", job_id)
        except Exception as e:
            print(f"⚠️ Не удалось добавить задачу (ID {schedule.id}): {e}")


async def schedule_habit_reminder(telegram_id: int, habit_name: str):
    """Отправляет напоминание для конкретной привычки пользователя"""
    async with async_session() as session:
        try:
            logging.info(f"✅ Напоминание вызвано для {telegram_id}, привычка: {habit_name}")

            result = await session.execute(
                select(User)
                .where(User.telegram_id == telegram_id)
                .options(selectinload(User.habits).selectinload(Habit.schedules))
            )
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"Пользователь с Telegram ID {telegram_id} не найден")

            # Найти нужную привычку
            habit = next((h for h in user.habits if h.name_habit == habit_name), None)
            if not habit:
                logging.warning(f"Привычка «{habit_name}» не найдена у пользователя {telegram_id}")
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"Привычка «{habit_name}» не найдена у пользователя {telegram_id}"
                )
                return

            if habit.is_completed:
                logging.info(f"Привычка {habit_name} уже выполнена сегодня.")
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"Привычка {habit_name} уже выполнена сегодня. 🕒"
                )
                return

            if habit.schedules:
                await bot.send_message(
                    chat_id=telegram_id,
                    text=f"Напоминание: не забудьте выполнить привычку «{habit_name}» 🕒"
                )
                logging.info(f"Напоминание отправлено для привычки {habit_name}")

        except Exception as e:
            logging.error(f"Ошибка при отправке напоминания: {e}")


DEFAULT_HABIT_DAYS = 21  # Можешь вынести в настройки


async def carry_over_unfinished_habits():
    async with async_session() as session:
        result = await session.execute(
            select(Habit)
            .where(Habit.is_completed == False)
            .options(selectinload(Habit.schedules), selectinload(Habit.user))
        )
        unfinished_habits = result.scalars().all()

        for habit in unfinished_habits:
            days_passed = (datetime.now().date() - habit.created_at.date()).days
            habit_days_required = habit.user.habit_days or DEFAULT_HABIT_DAYS

            if days_passed >= habit_days_required:
                continue

            # Копируем привычку
            new_habit = Habit(
                user_id=habit.user_id,
                name_habit=habit.name_habit,
                created_at=datetime.now(),
                is_completed=False
            )
            session.add(new_habit)
            await session.flush()

            # Копируем расписание и добавляем в планировщик
            for schedule in habit.schedules:
                new_schedule = UserSchedule(
                    habit_id=new_habit.id,
                    time=schedule.time
                )
                session.add(new_schedule)

                hour, minute = map(int, schedule.time.split(":"))
                job_id = f"reminder_{new_schedule.id}"
                scheduler.add_job(
                    schedule_habit_reminder,
                    trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
                    args=[habit.user.telegram_id, habit.name_habit],
                    id=job_id,
                    replace_existing=True
                )

            await bot.send_message(
                chat_id=habit.user.telegram_id,
                text=(
                    f"Привычка «{habit.name_habit}» перенесена на следующий день, "
                    f"так как она не была выполнена сегодня.\n"
                    f"Осталось {habit_days_required - days_passed} дней до закрепления привычки 💪"
                )
            )

        await session.commit()
        logging.info("⏭️ Невыполненные привычки перенесены на следующий день.")


async def reset_habit_completion():
    async with async_session() as session:
        await session.execute(update(Habit).values(is_completed=False))
        await session.commit()
        scheduler.add_job(
            carry_over_unfinished_habits,
            trigger=CronTrigger(hour=0, minute=0, timezone=TIMEZONE),
            id="carry_over_unfinished_habits",
            replace_existing=True
        )
        logging.info("Все привычки сброшены на не выполнены.")


def remove_jobs_by_habit_id(habit_id: int):
    for job in scheduler.get_jobs():
        if job.id.startswith(f"habit_{habit_id}_"):
            scheduler.remove_job(job.id)
