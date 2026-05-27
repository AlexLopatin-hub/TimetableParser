from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="base_router")


@router.message(Command("menu"))
async def display_menu(message: types.Message):
    await message.answer(
        "Доступные команды:\n"
        "/today — расписание на сегодня\n"
        "/week — расписание на неделю\n"
        "/change_group — сменить привязанную группу\n"
        "/search — найти группу по названию"
    )
