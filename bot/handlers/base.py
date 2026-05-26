from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="base_router")


@router.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Введи команду /daily_timetable или /weekly_timetable, чтобы получить расписание на неделю"
    )


@router.message(Command("menu"))
async def display_menu(message: types.Message):
    await message.answer(
        "Введи команду /daily_timetable или /weekly_timetable, чтобы получить расписание на неделю"
    )
