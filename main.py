import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.handlers import router as main_router
from core.config import settings
from parser.parser import Parser


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.tg_bot_api.get_secret_value())
    dp = Dispatcher()

    parser_client = Parser(url=f"{settings.uni_base_url}")

    dp.include_router(main_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, parser=parser_client)


if __name__ == "__main__":
    asyncio.run(main())
