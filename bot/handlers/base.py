from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from parser.parser import Parser
from storage.db import Database

router = Router(name="base_router")

_no_group_keyboard = (
    InlineKeyboardBuilder()
    .button(text="🔄 Выбрать группу", callback_data="chg_group_start")
    .as_markup()
)


async def show_main_menu(
    target: types.Message,
    db: Database,
    text_override: str | None = None,
) -> types.Message:
    """Show the user profile."""
    user_data = await db.get_user_data(target.from_user.id)

    if user_data:
        text = text_override or (
            f"👤 <b>Мой профиль</b>\n\n"
            f"📌 Группа: <b>{user_data['group_name']}</b>"
        )
    else:
        text = text_override or "👤 <b>Мой профиль</b>\n\n⚠️ Группа не выбрана."

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Сменить группу", callback_data="chg_group_start")
    builder.adjust(1)

    return await target.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.message(Command("start"))
async def start_command(
    message: types.Message,
    parser: Parser,
    db: Database,
    state: FSMContext,
):
    await state.clear()
    user_data = await db.get_user_data(message.from_user.id)
    if user_data:
        await show_main_menu(message, db)
    else:
        await message.answer(
            "👋 Добро пожаловать! Чтобы начать, выберите свою группу.",
            reply_markup=_no_group_keyboard,
        )


@router.message(Command("menu"))
async def display_menu(
    message: types.Message,
    db: Database,
    state: FSMContext,
):
    await state.clear()
    await show_main_menu(message, db)


@router.message(Command("cancel"))
async def cancel_action(
    message: types.Message,
    state: FSMContext,
    db: Database,
):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("🚫 Действие отменено.")
    await show_main_menu(message, db)
