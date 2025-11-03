import logging
from typing import Any, Optional

import asyncpg

from core.models import Wish


class Storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def ensure_session_schema(self) -> None:
        """Ensure the auxiliary table for user session tracking exists."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id BIGINT PRIMARY KEY,
                    is_active BOOLEAN NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

    async def set_session_state(self, user_id: int, is_active: bool) -> None:
        """Persist the desired session state for a given user."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_sessions (user_id, is_active, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id)
                DO UPDATE
                SET is_active = EXCLUDED.is_active,
                    updated_at = NOW()
                """,
                user_id,
                is_active,
            )

    async def mark_session_active(self, user_id: int) -> None:
        await self.set_session_state(user_id, True)

    async def mark_session_inactive(self, user_id: int) -> None:
        await self.set_session_state(user_id, False)

    async def is_session_active(self, user_id: int) -> bool:
        """Return True when a persisted session token exists for the user."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT is_active
                FROM user_sessions
                WHERE user_id = $1
                """,
                user_id,
            )
            if row is None:
                return False
            return bool(row["is_active"])

    @staticmethod
    def _row_to_wish(row: Optional[asyncpg.Record]) -> Wish | None:
        if row is None:
            return None
        return Wish(
            id=row["id"],
            title=row["title"],
            link=row["link"],
            category=row["category"],
            description=row["description"],
            priority=row["priority"],
            image=row["image"],
            image_url=row["image_url"],
        )

    async def _update_and_fetch(self, query: str, *args: Any) -> Wish | None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(query, *args)
        return self._row_to_wish(row)

    async def list_wishes(self, user_id: int) -> list[Wish]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, link, category, description, priority, image, image_url
                FROM wishes
                WHERE user_id = $1
                ORDER BY category, priority DESC
                """,
                user_id,
            )
        wishes: list[Wish] = []
        for row in rows:
            wish = self._row_to_wish(row)
            if wish is not None:
                wishes.append(wish)
        return wishes

    async def add_wish(self, user_id: int, wish: Wish) -> None:
        """
        Add a new wish to the database.

        Args:
            user_id (int): The ID of the user adding the wish.
            wish (Wish): The wish object containing details to be added.

        Raises:
            asyncpg.PostgresError: If there is an error during the database operation.
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO wishes (user_id, title, link, category, description, priority, image, image_url)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    user_id,
                    *wish.as_tuple(),
                )
        except asyncpg.PostgresError as exc:
            logging.error("Failed to add wish for user %s: %s", user_id, exc)
            raise

    async def find_wish(self, user_id: int, wish_id: int) -> Wish | None:
        wish_id = int(wish_id)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, title, link, category, description, priority, image, image_url
                FROM wishes
                WHERE user_id = $1 AND id = $2
                """,
                user_id,
                wish_id,
            )
        return self._row_to_wish(row)

    async def update_wish_title(self, user_id: int, wish_id: int, title: str) -> Wish | None:
        return await self._update_and_fetch(
            """
            UPDATE wishes
            SET title = $3
            WHERE user_id = $1 AND id = $2
            RETURNING id, title, link, category, description, priority, image, image_url
            """,
            user_id,
            wish_id,
            title,
        )

    async def update_wish_url(self, user_id: int, wish_id: int, url: str | None) -> Wish | None:
        return await self._update_and_fetch(
            """
            UPDATE wishes
            SET link = $3
            WHERE user_id = $1 AND id = $2
            RETURNING id, title, link, category, description, priority, image, image_url
            """,
            user_id,
            wish_id,
            url,
        )

    async def clear_wish_url(self, user_id: int, wish_id: int) -> Wish | None:
        return await self.update_wish_url(user_id, wish_id, None)

    async def update_wish_priority(self, user_id: int, wish_id: int, priority: int) -> Wish | None:
        return await self._update_and_fetch(
            """
            UPDATE wishes
            SET priority = $3
            WHERE user_id = $1 AND id = $2
            RETURNING id, title, link, category, description, priority, image, image_url
            """,
            user_id,
            wish_id,
            priority,
        )

    async def update_wish_photo(
        self,
        user_id: int,
        wish_id: int,
        *,
        file_id: str,
        image_bytes: bytes | None,
    ) -> Wish | None:
        return await self._update_and_fetch(
            """
            UPDATE wishes
            SET image_url = $3,
                image = $4
            WHERE user_id = $1 AND id = $2
            RETURNING id, title, link, category, description, priority, image, image_url
            """,
            user_id,
            wish_id,
            file_id,
            image_bytes,
        )

    async def clear_wish_photo(self, user_id: int, wish_id: int) -> Wish | None:
        return await self._update_and_fetch(
            """
            UPDATE wishes
            SET image_url = NULL,
                image = NULL
            WHERE user_id = $1 AND id = $2
            RETURNING id, title, link, category, description, priority, image, image_url
            """,
            user_id,
            wish_id,
        )

    async def delete_wish(self, user_id: int, wish_id: int) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM wishes
                WHERE user_id = $1 AND id = $2
                """,
                user_id,
                wish_id,
            )
        return result == "DELETE 1"
