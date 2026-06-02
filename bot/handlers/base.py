from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from parser.parser import Parser
from storage.db import Database

router = Router(name="base_router")

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Расписание на день")],
        [KeyboardButton(text="📆 Расписание на неделю")],
        [KeyboardButton(text="👤 Мой профиль")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие",
)

_no_group_keyboard = (
    InlineKeyboardBuilder()
    .button(text="🔄 Выбрать группу", callback_data="chg_group_start")
    .as_markup()
)


def build_main_menu_text(user_data: dict | None) -> str:
    if user_data:
        return (
            f"👋 Главное меню\n\n"
            f"📌 Ваша группа: <b>{user_data['group_name']}</b>"
        )
    return "👋 Главное меню\n\n⚠️ Группа не выбрана."


async def show_main_menu(
    target: types.Message,
    db: Database,
    text_override: str | None = None,
) -> types.Message:
    """Reply with the persistent main-menu keyboard."""
    user_data = await db.get_user_data(target.from_user.id)

    if user_data:
        text = text_override or build_main_menu_text(user_data)
        return await target.answer(text, reply_markup=main_keyboard, parse_mode="HTML")

    # No group — show inline button to pick one immediately
    text = text_override or build_main_menu_text(user_data)
    return await target.answer(
        text,
        reply_markup=_no_group_keyboard,
    )


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
        await message.answer("🚫 Действие отменено.", reply_markup=main_keyboard)
    else:
        await show_main_menu(message, db)
