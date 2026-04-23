
from aiogram import Router, F  
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,InlineKeyboardButton,CallbackQuery

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
def get_main_inline_key():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть сайт", url = "https://chat.deepseek.com/a/chat/s/fc32c22f-f538-491c-977e-ea80267f9dfc")],
            [InlineKeyboardButton(text="Подробнее",callback_data="info_more")]]
    )

    return keyboard



@router.callback_query(lambda c: c.data == "info_more")
async def process_more_info(callback:CallbackQuery):
    await callback.message.answer("Вот более подробная информация")
    await callback.answer()

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
    await message.answer(f"Информация про бота. Твое имя: {message.from_user.full_name}",reply_markup=get_main_inline_key())