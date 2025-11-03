import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
import asyncpg
from dotenv import load_dotenv

from bot.routes import register_routes
from core.config import ensure_token
from core.storage import Storage

logging.basicConfig(level=logging.INFO)

DATA_FILE = Path(__file__).with_name("wishlist_data.json")

bot = Bot(token=ensure_token(), default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

load_dotenv()

required_env_vars = ["PGUSER", "PGPASSWORD", "PGDATABASE", "PGHOST", "PGPORT"]
for var in required_env_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Переменная окружения {var} не установлена, но является обязательной.")

DB_CONFIG = {
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
    "database": os.getenv("PGDATABASE"),
    "host": os.getenv("PGHOST"),
    "port": int(os.getenv("PGPORT"))  # Удалено значение по умолчанию
}

async def create_pool():
    return await asyncpg.create_pool(**DB_CONFIG)


async def main() -> None:
    pool = await create_pool()
    storage = Storage(pool)
    try:
        await storage.ensure_session_schema()
        register_routes(dp, storage)
        await dp.start_polling(bot)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
