import logging
import asyncpg
from core.models import Wish


class Storage:
    def __init__(self, pool):
        self._pool = pool

    async def list_wishes(self, user_id: int):
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM wishes WHERE user_id=$1 ORDER BY category, priority DESC", user_id)
            return rows

    async def add_wish(self, user_id: int, wish: Wish):
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO wishes (user_id, title, link, category, description, priority) VALUES ($1, $2, $3, $4, $5, $6)",
                    user_id, wish.title, wish.link, wish.category, wish.description, wish.priority
                )
        except asyncpg.PostgresError as e:
            logging.error(f"Failed to add wish: {e}")
            raise
