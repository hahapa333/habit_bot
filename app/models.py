# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, BigInteger, Text, func
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime, server_default=func.now())

    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_habit = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    reminder_time = Column(String(5), nullable=True)  # формат HH:MM
    created_at = Column(DateTime, server_default=func.now())

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="habits")
    schedules = relationship("UserSchedule", back_populates="habit", cascade="all, delete-orphan")
    def __repr__(self):
        return f"<Habit(name='{self.name_habit}', user_id={self.user_id})>"


class UserSchedule(Base):
    __tablename__ = "user_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(String(5), nullable=False)  # формат HH:MM
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    habit = relationship("Habit", back_populates="schedules")

    def __repr__(self):
        return f"<UserSchedule(habit_id={self.habit_id}, time='{self.time}')>"

