import math
from collections import defaultdict

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from parser.parser import Parser
from storage.db import Database
from bot.handlers.base import show_main_menu

router = Router(name="groups_router")


# ---------------------------------------------------------------------------
# FSM  (only used for "enter group number manually")
# ---------------------------------------------------------------------------
class ChangeGroupState(StatesGroup):
    entering_number = State()


ITEMS_PER_PAGE = 10

_cached_faculties: list[dict] | None = None


# ===================================================================
#  Helpers – keyboard builders
# ===================================================================

async def _get_all_faculties_with_groups(parser: Parser) -> list[dict]:
    global _cached_faculties
    if _cached_faculties is not None:
        return _cached_faculties
    raw = await parser.get_faculties()
    filtered = [f for f in raw if await parser.get_groups_by_faculty(f["id"])]
    _cached_faculties = filtered
    return filtered


def _group_groups_by_level(groups: list[dict]) -> dict[int, list[dict]]:
    by_level = defaultdict(list)
    for g in groups:
        by_level[g.get("level", 0)].append(g)
    for level in by_level:
        by_level[level].sort(key=lambda g: g["name"])
    return by_level


# -- Faculties --------------------------------------------------------

def build_faculties_keyboard(
    faculties: list[dict], page: int = 0
) -> InlineKeyboardMarkup:
    total_pages = max(math.ceil(len(faculties) / ITEMS_PER_PAGE), 1)
    page = max(0, min(page, total_pages - 1))

    start = page * ITEMS_PER_PAGE
    chunk = faculties[start : start + ITEMS_PER_PAGE]

    builder = InlineKeyboardBuilder()
    for f in chunk:
        builder.button(text=f["name"][:50], callback_data=f"fac:{f['id']}")
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"fac_page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"fac_page:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="🚫 Отмена", callback_data="chg_cancel"))
    return builder.as_markup()


# -- Courses ----------------------------------------------------------

def build_courses_keyboard(
    levels: dict[int, list[dict]], faculty_id: int
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for level in sorted(levels.keys()):
        count = len(levels[level])
        builder.button(
            text=f"{level} курс ({count} групп)",
            callback_data=f"course:{faculty_id}:{level}",
        )
    builder.adjust(2)

    builder.row(
        InlineKeyboardButton(text="🔙 К факультетам", callback_data="fac_page:0"),
        InlineKeyboardButton(text="🚫 Отмена", callback_data="chg_cancel"),
    )
    return builder.as_markup()


# -- Groups -----------------------------------------------------------

def build_groups_keyboard(
    groups: list[dict], faculty_id: int, level: int, page: int = 0
) -> InlineKeyboardMarkup:
    total_pages = max(math.ceil(len(groups) / ITEMS_PER_PAGE), 1)
    page = max(0, min(page, total_pages - 1))

    start = page * ITEMS_PER_PAGE
    chunk = groups[start : start + ITEMS_PER_PAGE]

    builder = InlineKeyboardBuilder()
    for g in chunk:
        builder.button(text=g["name"], callback_data=f"grp:{g['id']}")
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀ Назад",
            callback_data=f"grp_page:{faculty_id}:{level}:{page - 1}",
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Вперёд ▶",
            callback_data=f"grp_page:{faculty_id}:{level}:{page + 1}",
        ))
    if nav:
        builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="🔙 К курсам", callback_data=f"fac:{faculty_id}"),
        InlineKeyboardButton(text="🚫 Отмена", callback_data="chg_cancel"),
    )
    return builder.as_markup()


# -- Method choice ----------------------------------------------------

def build_method_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти в списке", callback_data="chg_method:list")
    builder.button(text="✏️ Ввести номер вручную", callback_data="chg_method:manual")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🚫 Отмена", callback_data="chg_cancel"))
    return builder.as_markup()


# ===================================================================
#  Navigation helpers
# ===================================================================

async def show_faculties(
    target: types.Message | types.CallbackQuery,
    parser: Parser,
    page: int = 0,
):
    """Show faculty-selection page (used both from message and callback)."""
    is_callback = isinstance(target, types.CallbackQuery)

    if is_callback:
        await target.message.edit_text("⏳ Загружаю список факультетов...")
    else:
        await target.answer("⏳ Загружаю список факультетов...")

    faculties = await _get_all_faculties_with_groups(parser)
    if not faculties:
        error_text = "❌ Не удалось загрузить список факультетов. Попробуйте позже."
        if is_callback:
            await target.message.edit_text(error_text)
            await target.answer()
        else:
            await target.answer(error_text)
        return

    text = "Выберите факультет:"
    markup = build_faculties_keyboard(faculties, page)
    if is_callback:
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup)


# ===================================================================
#  Profile & change-group entry points
# ===================================================================

@router.message(F.text == "👤 Мой профиль")
async def show_profile(
    message: types.Message,
    db: Database,
):
    user_data = await db.get_user_data(message.from_user.id)

    if user_data:
        text = (
            f"👤 <b>Мой профиль</b>\n\n"
            f"📌 Группа: <b>{user_data['group_name']}</b>"
        )
    else:
        text = "👤 <b>Мой профиль</b>\n\n⚠️ Группа не выбрана."

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Сменить группу", callback_data="chg_group_start")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "chg_group_start")
async def on_change_group_start(callback: types.CallbackQuery, parser: Parser):
    """Show the two methods to select a new group."""
    global _cached_faculties
    _cached_faculties = None

    await callback.message.edit_text(
        "🔄 <b>Смена группы</b>\n\nВыберите способ:",
        reply_markup=build_method_choice_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("change_group"))
async def change_group_command(message: types.Message, parser: Parser):
    """Legacy command – redirect to the picker."""
    global _cached_faculties
    _cached_faculties = None
    await message.answer(
        "🔄 <b>Смена группы</b>\n\nВыберите способ:",
        reply_markup=build_method_choice_keyboard(),
        parse_mode="HTML",
    )


# ===================================================================
#  Method choice handler
# ===================================================================

@router.callback_query(F.data.startswith("chg_method:"))
async def on_method_chosen(callback: types.CallbackQuery, parser: Parser, state: FSMContext):
    method = callback.data.split(":", 1)[1]

    if method == "list":
        await show_faculties(callback, parser, page=0)

    elif method == "manual":
        await state.set_state(ChangeGroupState.entering_number)
        await callback.message.edit_text(
            "✏️ Введите номер группы (например: <code>3530904/10001</code>):\n\n"
            "Отправьте /cancel чтобы прервать.",
            parse_mode="HTML",
        )
        await callback.answer()


# ===================================================================
#  Manual number entry
# ===================================================================

@router.message(ChangeGroupState.entering_number, F.text)
async def process_manual_number(
    message: types.Message,
    parser: Parser,
    db: Database,
    state: FSMContext,
):
    raw = message.text.strip()

    if raw.startswith("/"):
        await state.clear()
        await message.answer("🚫 Поиск отменён.")
        await show_main_menu(message, db)
        return

    if len(raw) < 2:
        await message.answer("⚠️ Слишком короткий запрос. Введите хотя бы 2 символа.")
        return

    tmp = await message.answer("🔎 Проверяю группу в базе Политеха...")

    groups = await parser.search_group(raw)

    if not groups:
        await tmp.edit_text(
            "❌ Группа не найдена. Убедитесь, что написали её правильно "
            "(например: 3530904/10001).\n\nПопробуйте ещё раз или /cancel."
        )
        return

    if len(groups) == 1:
        g = groups[0]
        await db.set_user_group(message.from_user.id, g["id"], g["name"])
        await state.clear()
        await tmp.edit_text(
            f"✅ Группа «{g['name']}» успешно привязана!\n\n"
            "Вернитесь в меню /menu и выберите расписание."
        )
        await show_main_menu(message, db)
    else:
        await state.clear()
        builder = InlineKeyboardBuilder()
        for g in groups:
            builder.button(text=g["name"], callback_data=f"srch:{g['id']}")
        builder.adjust(1)
        builder.row(InlineKeyboardButton(text="🚫 Отмена", callback_data="chg_cancel"))
        await tmp.edit_text(
            f"🔎 Найдено {len(groups)} групп. Выберите одну:",
            reply_markup=builder.as_markup(),
        )


# ===================================================================
#  Cancel  (callback)
# ===================================================================

@router.callback_query(F.data == "chg_cancel")
async def on_change_cancel(callback: types.CallbackQuery, state: FSMContext, db: Database):
    await state.clear()
    await callback.message.edit_text("🚫 Смена группы отменена.")
    await callback.answer()
    await show_main_menu(callback.message, db)


# ===================================================================
#  Faculties → Courses → Groups  (unchanged navigation logic)
# ===================================================================

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

    faculty_name = "Неизвестный факультет"
    if callback.message.reply_markup and callback.message.reply_markup.inline_keyboard:
        for row in callback.message.reply_markup.inline_keyboard:
            for btn in row:
                if getattr(btn, "callback_data", None) == callback.data:
                    faculty_name = btn.text
                    break

    await callback.message.edit_text(f"⏳ Загружаю курсы факультета «{faculty_name}»...")

    groups = await parser.get_groups_by_faculty(faculty_id)
    if not groups:
        await callback.message.edit_text(
            f"❌ У факультета «{faculty_name}» не найдено групп.",
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
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Ошибка данных", show_alert=True)
        return
    faculty_id = int(parts[1])
    level = int(parts[2])

    await callback.message.edit_text(f"⏳ Загружаю группы {level} курса...")

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
        f"{level} курс\nВыберите группу:",
        reply_markup=build_groups_keyboard(level_groups, faculty_id, level),
    )
    await callback.answer()


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

    await db.set_user_group(callback.from_user.id, group_id, group_name)

    await callback.message.edit_text(
        f"✅ Группа «{group_name}» успешно привязана!\n\n"
        "Используйте меню для просмотра расписания."
    )
    await callback.answer("Группа сохранена ✅")


# ===================================================================
#  Legacy search  (keeps working)
# ===================================================================

class SearchState(StatesGroup):
    waiting_for_query = State()


def build_search_results_keyboard(groups: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in groups:
        builder.button(text=g["name"], callback_data=f"srch:{g['id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🚫 Отмена", callback_data="chg_cancel"))
    return builder.as_markup()


@router.message(Command("search"))
async def search_group_command(message: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer(
        "🔎 Введите название группы для поиска (например: 3530904/10001):"
    )


@router.message(SearchState.waiting_for_query)
async def process_search_query(
    message: types.Message,
    parser: Parser,
    db: Database,
    state: FSMContext,
):
    raw = message.text.strip()
    if len(raw) < 2:
        await message.answer("⚠️ Слишком короткий запрос. Введите хотя бы 2 символа.")
        return
    if raw.startswith("/"):
        await message.answer("🚫 Поиск отменён.")
        await state.clear()
        return

    tmp = await message.answer("🔎 Проверяю группу в базе Политеха...")
    groups = await parser.search_group(raw)

    if not groups:
        await tmp.edit_text(
            "❌ Группа не найдена. Убедитесь, что написали её правильно "
            "(например: 3530904/10001).\nПопробуйте ещё раз или другую команду."
        )
        return

    if len(groups) == 1:
        g = groups[0]
        await db.set_user_group(message.from_user.id, g["id"], g["name"])
        await state.clear()
        await tmp.edit_text(
            f"✅ Группа «{g['name']}» успешно привязана!\n\n"
            "Вернитесь в меню /menu и выберите расписание."
        )
    else:
        await state.clear()
        await tmp.edit_text(
            f"🔎 Найдено {len(groups)} групп. Выберите одну:",
            reply_markup=build_search_results_keyboard(groups),
        )



