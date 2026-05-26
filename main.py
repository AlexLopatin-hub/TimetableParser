import asyncio
import logging
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from parser.parser import Parser

logging.basicConfig(level=logging.INFO)

load_dotenv()
tg_api_key = os.getenv('TG_API_KEY', '')
uni_base_url = os.getenv('UNI_BASE_URL', '')


bot = Bot(token=tg_api_key)
dp = Dispatcher()


@dp.message(Command('start'))
async def start_command(message: types.Message):
    await message.answer('Введи команду /daily_timetable или /weekly_timetable, чтобы получить расписание на неделю')


@dp.message(Command('menu'))
async def display_menu(message: types.Message):
    await message.answer('Введи команду /daily_timetable или /weekly_timetable, чтобы получить расписание на неделю')


@dp.message(Command('daily_timetable'))
async def print_daily_timetable(message: types.Message):
    parser = Parser(uni_base_url)
    await message.answer(parser.get_daily_timetable())


@dp.message(Command('weekly_timetable'))
async def print_weekly_timetable(message: types.Message):
    parser = Parser(uni_base_url)
    await message.answer(parser.get_weekly_timetable())


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
