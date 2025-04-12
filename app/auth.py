from app.schemas import HabitCreate, UserCreate
from app.config import settings
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")  # Пример корректного значения

users_db = {"test_user": {"username": "test_user", "password": "hashed_password"}}



# Функция для создания JWT-токена
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.BOT_TOKEN, algorithm=settings.ALGORITHM)  # Генерация токена
    return encoded_jwt


# Получение текущего пользователя из JWT-токена
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.BOT_TOKEN, algorithms=[settings.ALGORITHM])  # Декодирование токена
        username: str = payload.get("sub")  # "sub" будет содержать имя пользователя
        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
            )
        # Ищем пользователя в "базе данных"
        user = users_db.get(username)

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
            )
        return user
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
        )
