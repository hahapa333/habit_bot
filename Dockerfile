# FROM python:3.10.12-buster
#
# # Системные переменные окружения
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1
# ENV PYTHONPATH=/code
#
# RUN ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime && echo "Europe/Moscow" > /etc/timezone
# # Шаг 1: Установка системных зависимостей
# RUN apt-get update && apt-get install -y --no-install-recommends python3-dev\
#     && rm -rf /var/lib/apt/lists/*
#
# # Обновляем pip и устанавливаем Poetry
# RUN pip install --upgrade pip \
#     && pip install poetry==1.5.1
#
# # Переход в каталог приложения
# WORKDIR /code
#
# # Добавление проекта
# COPY pyproject.toml .
# # добавьте, если файл существует
# COPY poetry.lock .
#
# RUN poetry config virtualenvs.create false \
#     && poetry check \
#     && poetry install --no-root --no-interaction --no-ansi
#
# # Создаем пользователя и настраиваем права
# RUN groupadd -r appgroup && useradd -ms /bin/bash -g appgroup appuser \
#     && mkdir -p /code/data/db
#
#
# # Переход на пользователя
# USER appuser
#
# # Копируем файлы
# COPY --chown=appuser:appgroup . .
#
# # Открытие порта
# EXPOSE 8000

# Используем официальный Python-образ
FROM python:3.10-slim

WORKDIR /app

# Poetry
RUN pip install --upgrade pip && pip install poetry

# Копируем зависимости
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
 && poetry install --no-dev --no-root

# Копируем проект
COPY . .

# Указываем порт, который Render слушает
EXPOSE 8000

# Команда запуска FastAPI приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

