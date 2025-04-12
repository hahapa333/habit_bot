from datetime import timedelta
from typing import Dict

from fastapi import FastAPI, Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import HabitCreate, UserCreate
from models_db.models import Habit, Base, User
from models_db.database import get_db, engine
# from fastapi.security import OAuth2PasswordRequestForm
# from app.auth import create_access_token, get_current_user
from app.config import settings
from app.schemas import HabitCreate, UserCreate

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

users_db: Dict[str, UserCreate] = {
    "example_user": UserCreate(
        username="example_user",
        hashed_password=pwd_context.hash("password"),
        telegram_id=12345
    )
}

# Генерация таблиц при старте сервера
@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        # Генерирует таблицы в базе данных
        await conn.run_sync(Base.metadata.create_all)


@app.post("/habits/")
async def create_habit(habit: HabitCreate,
                       db: AsyncSession = Depends(get_db) # Получаем текущего пользователя
                       ):
    try:
        new_habit = Habit(name_habit=habit.name_habit,
                          description=habit.description,
                          user_id=2)
        db.add(new_habit)
        await db.commit()
        await db.refresh(new_habit)
        return new_habit
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create habit {e}")


@app.get("/habits/")
async def get_habits(db: AsyncSession = Depends(get_db)):
    habits = await db.execute(select(Habit))
    return [habit for habit in habits.scalars()]


@app.post("/register/")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await db.execute(select(User).where(User.username == user.username))
    if existing_user.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(user.hashed_password)
    new_user = User(
        username=user.username,
        hashed_password=hashed_password,
        telegram_id=user.telegram_id  # Указываем значение telegram_id
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# @app.post("/token")
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     # users_db = {"test_user": {"username": "test_user", "password": "hashed_password"}}
#     user = users_db.get(form_data.username)  # Поиск пользователя в "базе данных"
#     if not user or not pwd_context.verify(form_data.password, user["hashed_password"]):
#         # Проверка пароля
#         raise HTTPException(
#             status_code=401,
#             detail="Incorrect username or password",
#         )
#     access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user["username"]}, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token,
#             "token_type": "bearer",
#             "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
#             "username": user.username
#             }
