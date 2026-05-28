from aiogram import Router, types
from aiogram.filters import Command

from parser.parser import Parser

from bot.handlers.groups import show_faculties
from storage.db import Database

router = Router(name="base_router")

@router.message(Command("start"))
async def start_command(message: types.Message, parser: Parser, db: Database):
    user_data = await db.get_user_data(message.from_user.id)

    if user_data:
        await message.answer(
            f"Ваша группа: {user_data['group_name']}\n"
            "Используйте /today или /week для расписания, /change_group для смены группы."
        )
        return

    await show_faculties(message, parser, page=0)


@router.message(Command("menu"))
async def display_menu(message: types.Message, parser: Parser, db: Database):
    user_data = await db.get_user_data(message.from_user.id)

    if not user_data:
        await show_faculties(message, parser, page=0)
        return

    await message.answer(
        f"Ваша группа: {user_data['group_name']}\n\n"
        "Доступные команды:\n"
        "/today — расписание на сегодня\n"
        "/week — расписание на неделю\n"
        "/change_group — сменить привязанную группу\n"
        "/search — найти группу по названию"
    )
