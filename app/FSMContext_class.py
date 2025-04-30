# Определение состояний для добавления привычки
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


class HabitForm(StatesGroup):
    name = State()  # Состояние для ввода названия привычки
    times = State()  # Состояние для ввода времени напоминаний


# Определение состояний для редактирования расписания привычки
class EditScheduleForm(StatesGroup):
    habit_id = State()  # Состояние для ввода ID привычки
    new_times = State()  # Состояние для ввода нового времени


# Определение состояний для редактирования привычки
class EditHabitForm(StatesGroup):
    habit_id = State()  # Состояние для ввода ID привычки
    new_habit = State()  # Состояние для ввода новой привычки