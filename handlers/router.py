
from aiogram import Router, F  
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


router = Router()


def get_main_reply_key():
    keyboard = ReplyKeyboardMarkup(
        keyboard= [
            [KeyboardButton(text = "О боте")],
            [KeyboardButton(text="Старт"),KeyboardButton(text='Помощь')]
        ],
        resize_keyboard=True
    )

    return keyboard

@router.message(Command("start"))
@router.message(F.text.lower() == "старт")
async def start(message:Message):
    print('start')
    await message.answer("Бот работает")


@router.message(Command("help"))
async def help(message:Message):
    print('help')
    await message.answer(" HELP \n/start \n/help \n/about",
                         reply_markup=get_main_reply_key())
    
@router.message(Command("about"))
async def about(message:Message):
    print('about')
    await message.answer(f"Информация про бота. Твое имя: {message.from_user.full_name}")