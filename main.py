import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher

from bot.handlers import router as main_router
from core.config import settings
from parser.parser import Parser
from storage.db import Database


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.tg_bot_api.get_secret_value())
    dp = Dispatcher()

    parser_client = Parser(base_url=f"{settings.uni_base_url}")
    db = Database()
    # session = aiohttp.ClientSession(
    #     connector=aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
    # )
    # dp["http_session"] = session

    await db.init_db()

    dp.include_router(main_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, parser=parser_client, db=db)


if __name__ == "__main__":
    asyncio.run(main())
