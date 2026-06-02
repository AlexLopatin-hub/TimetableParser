from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from parser.parser import Parser
from storage.db import Database
from bot.handlers.base import show_main_menu

router = Router(name="timetable_router")


@router.message(F.text == "📅 Расписание на день")
@router.message(Command("today"))
async def print_daily_timetable(
    message: types.Message,
    parser: Parser,
    db: Database,
    state: FSMContext,
):
    await _show_timetable(message, parser, db, state, mode="day")


@router.message(F.text == "📆 Расписание на неделю")
@router.message(Command("week"))
async def print_weekly_timetable(
    message: types.Message,
    parser: Parser,
    db: Database,
    state: FSMContext,
):
    await _show_timetable(message, parser, db, state, mode="week")


async def _show_timetable(
    message: types.Message,
    parser: Parser,
    db: Database,
    state: FSMContext,
    *,
    mode: str,
):
    await state.clear()

    user_data = await db.get_user_data(message.from_user.id)

    if not user_data:
        await show_main_menu(
            message,
            db,
            text_override="⚠️ Сначала выберите группу.\n\nНажмите «👤 Мой профиль» → «Сменить группу».",
        )
        return

    current_date = datetime.now().strftime("%Y-%m-%d")

    if mode == "day":
        text = await parser.get_daily_timetable(
            group_id=user_data["group_id"], date_str=current_date
        )
    else:
        text = await parser.get_weekly_timetable(
            group_id=user_data["group_id"], date_str=current_date
        )

    if text is None:
        await message.answer("❌ Не удалось получить расписание. Попробуйте позже.")
        return

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("srch:"))
async def on_search_result_selected(
    callback: types.CallbackQuery,
    parser: Parser,
    db: Database,
):
    group_id = int(callback.data.split(":")[1])

    group_name = "Неизвестная группа"
    if callback.message.reply_markup and callback.message.reply_markup.inline_keyboard:
        for row in callback.message.reply_markup.inline_keyboard:
            for btn in row:
                if getattr(btn, "callback_data", None) == callback.data:
                    group_name = btn.text
                    break

    await db.set_user_group(
        user_id=callback.from_user.id,
        group_id=group_id,
        group_name=group_name,
    )

    await callback.message.edit_text(
        f"✅ Группа «{group_name}» успешно привязана!",
    )
    await callback.answer("Группа сохранена ✅")


@router.callback_query(F.data == "srch_cancel")
async def on_search_cancelled(callback: types.CallbackQuery, db: Database):
    await callback.message.edit_text("🚫 Поиск отменён.")
    await callback.answer()
    await show_main_menu(callback.message, db)
