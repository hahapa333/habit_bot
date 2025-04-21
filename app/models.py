from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, func, Boolean, BigInteger
# from sqlalchemy.ext.declarative import  declarative_base
from sqlalchemy.orm import relationship,declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, nullable=False, server_default="true")
    hashed_password = Column(String(255), nullable=False)  # Хэшированный пароль
    # Связь с привычками
    habits = relationship("Habit", back_populates="user", cascade="all")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', telegram_id='{self.telegram_id}')>"


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_habit = Column(String(100), nullable=False)
    description = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    is_completed = Column(Boolean, default=False)



    # Внешний ключ на пользователя
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Связь с пользователем
    user = relationship("User", back_populates="habits")

    def __repr__(self):
        return f"<Habit(id={self.id}, name_habit='{self.name_habit}', user_id={self.user_id})>"

