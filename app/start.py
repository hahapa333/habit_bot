from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def start(message: Message):
    await message.answer("Hello!")


# функция эхо-бот
@router.message()
async def echo_handler(message: Message) -> None:
    await message.answer(f'Повторяю: <b>{message.text}</b>')
