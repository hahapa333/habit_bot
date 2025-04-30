# 🧠 Habit Tracker Telegram Bot

Телеграм-бот для отслеживания привычек с напоминаниями и Webhook. Использует FastAPI, PostgreSQL и Docker. Поддерживает автоматические напоминания, редактирование привычек и ежедневный сброс статуса.

## 🚀 Возможности

- Добавление/удаление/редактирование привычек
- Напоминания по расписанию (APScheduler)
- FSM-состояния для пользовательского взаимодействия
- Webhook или Polling режим
- Поддержка Docker и Docker Compose
- PostgreSQL + Alembic для миграций

---

## 🛠️ Технологии

- [FastAPI](https://fastapi.tiangolo.com)
- [SQLAlchemy 2.0 async](https://docs.sqlalchemy.org)
- [Aiogram 3.x](https://docs.aiogram.dev)
- [APScheduler](https://apscheduler.readthedocs.io)
- [Docker](https://www.docker.com/)
- [Alembic](https://alembic.sqlalchemy.org)

---

## 📦 Установка локально


## 📄 .env переменные
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/habit_db
WEBHOOK_URL=https://your-domain.com
WEBHOOK_PATH=/webhook/your_bot_token
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8000

📡 Установка Webhook вручную

curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=<WEBHOOK_URL><WEBHOOK_PATH>

## ☁️ Деплой на VPS

# Подключись к VPS
ssh root@your-server-ip

## 🛠 Команды бота

/start — регистрация
/addhabit — добавить привычку
/habit_list — список привычек
/delete_schedule — удалить расписание
/help — справка

# Установи Docker и клонируй проект
apt update && apt install -y docker.io docker-compose
git clone https://github.com/your-user/habit-bot.git
cd habit-bot

# Установи .env и запусти
docker-compose up --build -d


🧩 Миграции Alembic

# Создать миграцию
poetry run alembic revision --autogenerate -m "init"

# Применить миграции
poetry run alembic upgrade head



