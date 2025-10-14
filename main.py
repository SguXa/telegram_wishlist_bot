import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.routes import register_routes
from core.config import AUTHORIZED_NUMERIC_IDS, ensure_token
from core.storage import Storage

logging.basicConfig(level=logging.INFO)

DATA_FILE = Path(__file__).with_name("wishlist_data.json")

storage = Storage(DATA_FILE, AUTHORIZED_NUMERIC_IDS)
storage.load()

bot = Bot(token=ensure_token(), default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
register_routes(dp, storage)



async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

