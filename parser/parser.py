from typing import Any, Optional

import aiohttp
from storage.cache import cached


WEEKDAY_NAMES = {
    1: "ПН", 2: "ВТ", 3: "СР", 4: "ЧТ", 5: "ПТ", 6: "СБ", 7: "ВС"
}


def _fmt_date(iso_date: str) -> str:
    """Convert YYYY-MM-DD or YYYY.MM.DD to DD.MM.YYYY."""
    try:
        clean = iso_date.strip().replace(".", "-")
        y, m, d = clean.split("-")
        return f"{d}.{m}.{y}"
    except (ValueError, AttributeError):
        return iso_date


class Parser:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @cached(ttl=86400)  # 24 часа
    async def search_group(self, group_name: str) -> list[dict[str, Any]]:
        """Search groups by name. Returns a list of matching groups (id + name)."""
        url = f"{self.base_url}/api/v1/ruz/search/groups"
        params = {"q": group_name}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("groups", [])
            except Exception:
                pass
        return []

    @cached(ttl=86400)  # 24 часа
    async def get_faculties(self) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/ruz/faculties"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("faculties", [])
            except Exception:
                pass
        return []

    @cached(ttl=86400)  # 24 часа
    async def get_groups_by_faculty(self, faculty_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/ruz/faculties/{faculty_id}/groups"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("groups", [])
            except Exception:
                pass
        return []

    @cached(ttl=3600)  # 1 час для расписания, так как оно может обновляться
    async def _fetch_schedule(self, group_id: int, date_str: str) -> Optional[dict[str, Any]]:
        """Fetch raw schedule from the scheduler endpoint."""
        url = f"{self.base_url}/api/v1/ruz/scheduler/{group_id}"
        params = {"date": date_str}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
            except Exception:
                pass
        return None

    def _format_day(self, label: str, lessons: list[dict]) -> str:
        """Format a single day's lessons into a readable string."""
        if not lessons:
            return ""

        lines = [label, "━" * 28]
        for i, lesson in enumerate(lessons):
            time_start = lesson.get("time_start", "??:??")
            time_end = lesson.get("time_end", "??:??")
            subject = lesson.get("subject", "—")
            type_obj = lesson.get("typeObj", {})
            lesson_type = type_obj.get("name", "") if type_obj else ""

            teachers = lesson.get("teachers") or []
            teacher_names = ", ".join(t.get("full_name", "") for t in teachers)

            auditories = lesson.get("auditories") or []
            places = []
            for a in auditories:
                building_abbr = a.get("building", {}).get("abbr", "")
                room = a.get("name", "")
                places.append(f"{room}, {building_abbr}" if building_abbr else room)
            place_str = " | ".join(places)

            lines.append(f"📌 <b>{subject}</b>")
            if lesson_type:
                lines.append(f"   <i>{lesson_type}</i>")
            lines.append(f"   🕐 {time_start} – {time_end}")
            if teacher_names:
                lines.append(f"   👤 {teacher_names}")
            if place_str:
                lines.append(f"   📍 {place_str}")
            if i < len(lessons) - 1:
                lines.append("")

        return "\n".join(lines)

    async def get_daily_timetable(self, group_id: int, date_str: str) -> Optional[str]:
        """Return formatted timetable for a specific date."""
        data = await self._fetch_schedule(group_id, date_str)
        if not data:
            return None

        days = data.get("days") or []
        if not days:
            return "На эту дату занятий нет."

        # Find matching day
        for day in days:
            if day.get("date") == date_str:
                weekday_num = day.get("weekday", 0)
                weekday = WEEKDAY_NAMES.get(weekday_num, "")
                lessons = day.get("lessons") or []
                if not lessons:
                    label = f"{weekday}, {_fmt_date(date_str)}" if weekday else _fmt_date(date_str)
                    return f"{label}\n───────────────\nВыходной / пар нет 🎉"
                label = f"{weekday}, {_fmt_date(day['date'])}" if weekday else _fmt_date(day["date"])
                return self._format_day(label, lessons)

        return f"{_fmt_date(date_str)}\n───────────────\nВыходной / пар нет 🎉"

    async def get_weekly_timetable(self, group_id: int, date_str: str) -> Optional[str]:
        """Return formatted timetable for the week containing date_str."""
        data = await self._fetch_schedule(group_id, date_str)
        if not data:
            return None

        week = data.get("week") or {}
        days = data.get("days") or []
        if not days:
            return "На этой неделе занятий нет."

        week_start = week.get("date_start", "")
        week_end = week.get("date_end", "")

        all_parts = []
        header = f"📅 Неделя {_fmt_date(week_start)} – {_fmt_date(week_end)}"
        if week.get("is_odd"):
            header += " (нечётная)"
        else:
            header += " (чётная)"
        all_parts.append(header)
        all_parts.append("")

        for day in days:
            lessons = day.get("lessons") or []
            weekday_num = day.get("weekday", 0)
            day_date = day.get("date", "")
            day_label = f"{WEEKDAY_NAMES.get(weekday_num, '?')}, {_fmt_date(day_date) if day_date else ''}".strip()

            if not lessons:
                block = f"▫ {day_label}\n   (занятий нет)"
            else:
                block = self._format_day(day_label, lessons)
            all_parts.append(block)

        return "\n\n".join(all_parts)
