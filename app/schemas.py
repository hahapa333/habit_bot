from typing import Optional

from pydantic import BaseModel, Field


class HabitCreate(BaseModel):
    name_habit: str
    description: str


class UserCreate(BaseModel):
    username: str
    hashed_password: str
    telegram_id: int  # Добавляем поле telegram_id
