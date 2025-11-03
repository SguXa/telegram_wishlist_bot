import asyncpg
import logging

async def create_tables(pool: asyncpg.Pool) -> None:
    """
    Create all necessary tables in the database.

    Args:
        pool (asyncpg.Pool): The connection pool to the database.

    Raises:
        asyncpg.PostgresError: If there is an error during table creation.
    """
    create_wishes_table = """
    CREATE TABLE IF NOT EXISTS wishes (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        title TEXT NOT NULL,
        link TEXT,
        category TEXT,
        description TEXT,
        priority INTEGER,
        image BYTEA,
        image_url TEXT
    );
    """

    try:
        async with pool.acquire() as conn:
            await conn.execute(create_wishes_table)
            logging.info("Tables created successfully.")
    except asyncpg.PostgresError as e:
        logging.error(f"Failed to create tables: {e}")
        raise
