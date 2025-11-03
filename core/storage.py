import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

import asyncpg

from core.models import Store, Wish


class Storage:
    def __init__(self, pool):
        self._pool = pool

    async def list_wishes(self, user_id: int):
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM wishes WHERE user_id=$1 ORDER BY category, priority DESC", user_id)
            return rows

    async def add_wish(self, user_id: int, title: str, link: str = None, category: str = None, description: str = None, priority: int = None):
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO wishes (user_id, title, link, category, description, priority) VALUES ($1, $2, $3, $4, $5, $6)",
                user_id, title, link, category, description, priority
            )
