from aiogram import Router

from .base import router as base_router
from .groups import router as groups_router
from .timetable import router as timetable_router

router = Router(name="main_router")
router.include_routers(base_router, groups_router, timetable_router)
