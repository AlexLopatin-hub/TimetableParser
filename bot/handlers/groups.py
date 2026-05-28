import math
from collections import defaultdict

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from parser.parser import Parser
from storage.db import Database

class SearchState(StatesGroup):
    waiting_for_query = State()


router = Router(name="groups_router")

ITEMS_PER_PAGE = 10

_cached_faculties: list[dict] | None = None


async def _get_all_faculties_with_groups(parser: Parser) -> list[dict]:
    """Fetch all faculties and filter out those that have no groups."""
    global _cached_faculties
    if _cached_faculties is not None:
        return _cached_faculties

    raw = await parser.get_faculties()
    filtered = []
    for f in raw:
        groups = await parser.get_groups_by_faculty(f["id"])
        if groups:
            filtered.append(f)
    _cached_faculties = filtered
    return filtered


def _group_groups_by_level(groups: list[dict]) -> dict[int, list[dict]]:
    """Group groups by level, sort each list by name."""
    by_level = defaultdict(list)
    for g in groups:
        by_level[g.get("level", 0)].append(g)
    for level in by_level:
        by_level[level].sort(key=lambda g: g["name"])
    return by_level


def build_faculties_keyboard(faculties: list[dict], page: int = 0) -> types.InlineKeyboardMarkup:
    total_pages = max(math.ceil(len(faculties) / ITEMS_PER_PAGE), 1)
    page = max(0, min(page, total_pages - 1))

    start = page * ITEMS_PER_PAGE
    chunk = faculties[start : start + ITEMS_PER_PAGE]

    builder = InlineKeyboardBuilder()
    for f in chunk:
        builder.button(text=f["name"][:50], callback_data=f"fac:{f['id']}")
    builder.adjust(1)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="◀ Назад", callback_data=f"fac_page:{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton(text="Вперёд ▶", callback_data=f"fac_page:{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()


async def show_faculties(message: types.Message, parser: Parser, page: int):
    msg = await message.answer("Загружаю список факультетов...")

    faculties = await _get_all_faculties_with_groups(parser)
    if not faculties:
        await msg.edit_text("Не удалось загрузить список факультетов. Попробуйте позже.")
        return

    await msg.edit_text(
        "Выберите факультет:",
        reply_markup=build_faculties_keyboard(faculties, page),
    )


def build_courses_keyboard(levels: dict[int, list[dict]], faculty_id: int) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for level in sorted(levels.keys()):
        count = len(levels[level])
        builder.button(
            text=f"{level} курс ({count} групп)",
            callback_data=f"course:{faculty_id}:{level}",
        )
    builder.adjust(2)

    builder.row(types.InlineKeyboardButton(text="🔙 К факультетам", callback_data="fac_page:0"))
    return builder.as_markup()


def build_groups_keyboard(
    groups: list[dict], faculty_id: int, level: int, page: int = 0
) -> types.InlineKeyboardMarkup:
    total_pages = max(math.ceil(len(groups) / ITEMS_PER_PAGE), 1)
    page = max(0, min(page, total_pages - 1))

    start = page * ITEMS_PER_PAGE
    chunk = groups[start : start + ITEMS_PER_PAGE]

    builder = InlineKeyboardBuilder()
    for g in chunk:
        builder.button(text=g["name"], callback_data=f"grp:{g['id']}")
    builder.adjust(1)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="◀ Назад", callback_data=f"grp_page:{faculty_id}:{level}:{page - 1}"
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="Вперёд ▶", callback_data=f"grp_page:{faculty_id}:{level}:{page + 1}"
            )
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        types.InlineKeyboardButton(
            text="🔙 К курсам", callback_data=f"fac:{faculty_id}"
        )
    )
    return builder.as_markup()


@router.message(Command("change_group"))
async def change_group_command(message: types.Message, parser: Parser):
    global _cached_faculties
    _cached_faculties = None
    await show_faculties(message, parser, page=0)


@router.callback_query(F.data.startswith("fac_page:"))
async def on_faculty_page(callback: types.CallbackQuery, parser: Parser):
    page = int(callback.data.split(":")[1])

    faculties = await _get_all_faculties_with_groups(parser)
    if not faculties:
        await callback.answer("Не удалось загрузить факультеты", show_alert=True)
        return

    await callback.message.edit_text(
        "Выберите факультет:",
        reply_markup=build_faculties_keyboard(faculties, page),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fac:"))
async def on_faculty_selected(callback: types.CallbackQuery, parser: Parser):
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    faculty_id = int(parts[1])

    # Find faculty name from the button text
    faculty_name = "Неизвестный факультет"
    if callback.message.reply_markup and callback.message.reply_markup.inline_keyboard:
        for row in callback.message.reply_markup.inline_keyboard:
            for btn in row:
                if getattr(btn, "callback_data", None) == callback.data:
                    faculty_name = btn.text
                    break

    await callback.message.edit_text(f"Загружаю курсы факультета «{faculty_name}»...")

    groups = await parser.get_groups_by_faculty(faculty_id)
    if not groups:
        await callback.message.edit_text(
            f"У факультета «{faculty_name}» не найдено групп.",
            reply_markup=build_faculties_keyboard(
                await _get_all_faculties_with_groups(parser), 0
            ),
        )
        await callback.answer("Группы не найдены", show_alert=True)
        return

    levels = _group_groups_by_level(groups)

    await callback.message.edit_text(
        f"Факультет: {faculty_name}\nВыберите курс:",
        reply_markup=build_courses_keyboard(levels, faculty_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("course:"))
async def on_course_selected(callback: types.CallbackQuery, parser: Parser):
    # data: course:{faculty_id}:{level}
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    faculty_id = int(parts[1])
    level = int(parts[2])

    # Get course name from button text
    course_label = (
        callback.message.reply_markup.inline_keyboard and
        next(
            (row[0].text for row in callback.message.reply_markup.inline_keyboard
             if row and getattr(row[0], "callback_data", None) == callback.data),
            f"{level} курс"
        )
    )

    await callback.message.edit_text(f"Загружаю группы {course_label}...")

    groups = await parser.get_groups_by_faculty(faculty_id)
    if not groups:
        await callback.answer("Группы не найдены", show_alert=True)
        return

    levels = _group_groups_by_level(groups)
    level_groups = levels.get(level, [])
    if not level_groups:
        await callback.answer("Нет групп на этом курсе", show_alert=True)
        return

    await callback.message.edit_text(
        f"{course_label}\nВыберите группу:",
        reply_markup=build_groups_keyboard(level_groups, faculty_id, level),
    )
    await callback.answer()


def build_search_results_keyboard(groups: list[dict]) -> types.InlineKeyboardMarkup:
    """Build an inline keyboard with matching groups."""
    builder = InlineKeyboardBuilder()
    for g in groups:
        builder.button(text=g["name"], callback_data=f"srch:{g['id']}")
    builder.adjust(1)
    builder.row(types.InlineKeyboardButton(
        text="❌ Отмена", callback_data="srch_cancel"
    ))
    return builder.as_markup()


@router.message(Command("search"))
async def search_group_command(message: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer(
        "Введите название группы для поиска (например: 3530904/10001):"
    )


@router.message(SearchState.waiting_for_query)
async def process_search_query(message: types.Message, parser: Parser, db: Database, state: FSMContext):
    raw_input = message.text.strip()

    if len(raw_input) < 2:
        await message.answer("Слишком короткий запрос. Введите хотя бы 2 символа.")
        return

    if raw_input.startswith("/"):
        await message.answer("Поиск отменён.")
        await state.clear()
        return

    tmp_msg = await message.answer("Проверяю группу в базе Политеха...")

    groups = await parser.search_group(raw_input)

    if not groups:
        await tmp_msg.edit_text(
            "Группа не найдена. Убедитесь, что написали её правильно (например: 3530904/10001).\n"
            "Попробуйте ещё раз или используйте другую команду."
        )
        return

    if len(groups) == 1:
        g = groups[0]
        await db.set_user_group(
            user_id=message.from_user.id,
            group_id=g["id"],
            group_name=g["name"],
        )
        await state.clear()
        await tmp_msg.edit_text(
            f"Группа «{g['name']}» успешно привязана!\n"
            "Используйте /today для расписания на сегодня, /week — на неделю."
        )
    else:
        await state.clear()
        await tmp_msg.edit_text(
            f"Найдено {len(groups)} групп:\nВыберите одну:",
            reply_markup=build_search_results_keyboard(groups),
        )


@router.callback_query(F.data.startswith("grp_page:"))
async def on_group_page(callback: types.CallbackQuery, parser: Parser):
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    faculty_id = int(parts[1])
    level = int(parts[2])
    page = int(parts[3])

    groups = await parser.get_groups_by_faculty(faculty_id)
    if not groups:
        await callback.answer("Группы не найдены", show_alert=True)
        return

    levels = _group_groups_by_level(groups)
    level_groups = levels.get(level, [])
    if not level_groups:
        await callback.answer("Нет групп на этом курсе", show_alert=True)
        return

    await callback.message.edit_text(
        callback.message.text or "Выберите группу:",
        reply_markup=build_groups_keyboard(level_groups, faculty_id, level, page),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("grp:"))
async def on_group_selected(callback: types.CallbackQuery, parser: Parser, db: Database):
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
        f"Группа «{group_name}» успешно привязана!\n"
        "Используйте /today для расписания на сегодня, /week — на неделю."
    )
    await callback.answer("Группа сохранена ✅")
