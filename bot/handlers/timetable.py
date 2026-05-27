from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command

from parser.parser import Parser
from storage.db import Database

router = Router(name="timetable_router")


@router.message(Command("today"))
async def print_daily_timetable(message: types.Message, parser: Parser, db: Database):
    user_id = message.from_user.id

    user_data = await db.get_user_data(user_id)

    if not user_data:
        await message.answer(
            "Вы ещё не выбрали группу. Используйте /start для выбора."
        )
        return

    current_date = datetime.now().strftime("%Y-%m-%d")

    text = await parser.get_daily_timetable(
        group_id=user_data["group_id"], date_str=current_date
    )

    if text is None:
        await message.answer("Не удалось получить расписание. Попробуйте позже.")
        return

    await message.answer(text, parse_mode="HTML")


@router.message(Command("week"))
async def print_weekly_timetable(message: types.Message, parser: Parser, db: Database):
    user_id = message.from_user.id

    user_data = await db.get_user_data(user_id)

    if not user_data:
        await message.answer(
            "Вы ещё не выбрали группу. Используйте /start для выбора."
        )
        return

    current_date = datetime.now().strftime("%Y-%m-%d")

    text = await parser.get_weekly_timetable(
        group_id=user_data["group_id"], date_str=current_date
    )

    if text is None:
        await message.answer("Не удалось получить расписание. Попробуйте позже.")
        return

    await message.answer(text, parse_mode="HTML")


@router.message(Command("search"))
async def search_group_command(message: types.Message):
    await message.answer(
        "Введите название группы для поиска (например: 3530904/10001):"
    )


@router.message()
async def process_group_input(message: types.Message, parser: Parser, db: Database):
    raw_input = message.text.strip()

    if len(raw_input) < 2:
        return

    if raw_input.startswith("/"):
        return

    await message.answer("Проверяю группу в базе Политеха...")

    group_info = await parser.search_group(raw_input)

    if not group_info:
        await message.answer("Группа не найдена. Убедитесь, что написали её правильно (например: 3530904/10001).")
        return

    await db.set_user_group(
        user_id=message.from_user.id,
        group_id=group_info["id"],
        group_name=group_info["name"]
    )

    await message.answer(
        f"Группа {group_info['name']} успешно привязана.\n"
        "Используйте /today или /week для просмотра расписания."
    )
