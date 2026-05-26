from aiogram import Router, types
from aiogram.filters import Command

from parser.parser import Parser

router = Router(name="timetable_router")


@router.message(Command("daily_timetable"))
async def print_daily_timetable(message: types.Message, parser: Parser):
    res = await parser.get_daily_timetable()
    await message.answer(res)


@router.message(Command("weekly_timetable"))
async def print_weekly_timetable(message: types.Message, parser: Parser):
    res = await parser.get_weekly_timetable()
    await message.answer(res)
