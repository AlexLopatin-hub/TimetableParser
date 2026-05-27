import math
from collections import defaultdict

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from parser.parser import Parser
from storage.db import Database

router = Router(name="groups_router")

ITEMS_PER_PAGE = 10

# Cached data loaded once during navigation
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


# --- Faculty keyboard ---

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


# --- Course keyboard ---

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


# --- Group keyboard ---

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


# --- Handlers ---

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


@router.message(Command("change_group"))
async def change_group_command(message: types.Message, parser: Parser):
    global _cached_faculties
    _cached_faculties = None  # invalidate cache
    await show_faculties(message, parser, page=0)


# --- Faculty callbacks ---

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


# --- Course callbacks ---

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


# --- Group callbacks ---

@router.callback_query(F.data.startswith("grp_page:"))
async def on_group_page(callback: types.CallbackQuery, parser: Parser):
    # data: grp_page:{faculty_id}:{level}:{page}
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

    # Get group name from the button text
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
