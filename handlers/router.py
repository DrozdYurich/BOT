
from aiogram import Router, F  
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,InlineKeyboardButton,CallbackQuery
from form.user import Form
from aiogram.fsm.context import FSMContext
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
            [InlineKeyboardButton(text="Подробнее",callback_data="info_more")],
            [InlineKeyboardButton(text="Регистрация",callback_data="redistr")]]
    )

    return keyboard


@router.message(Command("cancel"))
async def cancel_form(message:Message, state: FSMContext):
    await state.clear()
    await message.answer("Анкета окончена")


@router.callback_query(lambda c: c.data == "info_more")
async def process_more_info(callback:CallbackQuery):
    await callback.message.answer("Вот более подробная информация")
    await callback.answer()


@router.callback_query(lambda c: c.data == "redistr")
async def process_registry(callback:CallbackQuery, state: FSMContext):
    await callback.message.answer("Давайте заполним анкету! \nВведите ваше имя:")
    await state.set_state(Form.name)
    await callback.answer()

@router.message(Form.name,F.text)
async def proccess_name(message:Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Отлично! \nВведите ваш возраст:")
    await state.set_state(Form.age)

@router.message(Form.age,F.text)
async def proccess_age(message:Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Число введите")
        return
    if int(message.text)<1 or int(message.text)>100:
        await message.answer("Введите корректный возраст")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Отлично! \nВведите ваш email:")
    await state.set_state(Form.email)

@router.message(Form.email,F.text)
async def proccess_email(message:Message, state: FSMContext):
    await state.update_data(email=message.text)
    data = await state.get_data()
    name = data["name"]
    age = data["age"]
    email = data["email"]

    await message.answer(f"Вы зарегестрировались!\nИмя: {name}\nВозраст: {age}\nПочта: {email}")
    await state.clear()




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


    