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

    async def find_wish(self, user_id: int, wish_id: int) -> Wish | None:
        """
        Найти желание по идентификатору пользователя и идентификатору желания.

        Args:
            user_id (int): Идентификатор пользователя.
            wish_id (int): Идентификатор желания.

        Returns:
            Optional[Wish]: Найденное желание или None, если не найдено.
        """
        wish_id = int(wish_id)  # Приведение wish_id к целому числу
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, title, link, category, description, priority, photo_file_id
                FROM wishes
                WHERE user_id=$1 AND id=$2
                """,
                user_id, wish_id
            )
            if row:
                return Wish(
                    id=row['id'],
                    title=row['title'],
                    link=row['link'],
                    category=row['category'],
                    description=row['description'],
                    priority=row['priority'],
                    photo_file_id=row['photo_file_id']
                )
            return None

    async def update_wish_field(self, user_id: int, wish_id: int, field: str, value: str | int) -> Wish | None:
        """
        Обновить указанное поле желания.

        Args:
            user_id (int): Идентификатор пользователя.
            wish_id (int): Идентификатор желания.
            field (str): Поле для обновления.
            value (str | int): Новое значение поля.

        Returns:
            Optional[Wish]: Обновленное желание или None, если обновление не удалось.
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE wishes
                SET {field} = $1
                WHERE user_id = $2 AND id = $3
                """,
                value, user_id, wish_id
            )
            return await self.find_wish(user_id, wish_id)

    async def delete_wish(self, user_id: int, wish_id: int) -> bool:
        """
        Удалить желание по идентификатору пользователя и идентификатору желания.

        Args:
            user_id (int): Идентификатор пользователя.
            wish_id (int): Идентификатор желания.

        Returns:
            bool: True, если желание было удалено, иначе False.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM wishes
                WHERE user_id = $1 AND id = $2
                """,
                user_id, wish_id
            )
            return result == "DELETE 1"
