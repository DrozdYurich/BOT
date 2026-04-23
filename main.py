from os import getenv
import asyncio
from aiogram import Bot,Dispatcher
from dotenv import load_dotenv
from handlers.router import router

load_dotenv()
TOKEN = getenv("BOT_TOKEN")


dp = Dispatcher()

dp.include_router(router)



async def main():
    bot= Bot(token=TOKEN)

    await dp.start_polling(bot)


asyncio.run(main())