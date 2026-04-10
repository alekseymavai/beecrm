"""apiary/bot.py — точка входа BEEBOTLITE Telegram бота пчеловода."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from apiary.config import BOT_TOKEN
from apiary.routers import admin, inspection, start

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # admin первым — перехватывает /adduser, /approve, /addhive до остальных
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(inspection.router)

    logger.info("BEEBOTLITE starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
