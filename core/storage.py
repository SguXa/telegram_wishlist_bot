import logging
import asyncpg
from core.models import Wish


class Storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def list_wishes(self, user_id: int) -> list[Wish]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, link, category, description, priority, photo_file_id
                FROM wishes
                WHERE user_id=$1
                ORDER BY category, priority DESC
                """,
                user_id
            )
            return [Wish(id=row['id'], title=row['title'], link=row['link'], category=row['category'], description=row['description'], priority=row['priority'], photo_file_id=row['photo_file_id']) for row in rows]

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
                    INSERT INTO wishes (user_id, title, link, category, description, priority)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    user_id, *wish.as_tuple()
                )
        except asyncpg.PostgresError as e:
            logging.error(f"Failed to add wish for user {user_id}: {e}")
            raise
