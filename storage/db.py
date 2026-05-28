import aiosqlite
from storage.cache import cached, clear_cache


class Database:
    def __init__(self, db_path: str = "storage.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    group_id INTEGER NOT NULL,
                    group_name TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def set_user_group(self, user_id: int, group_id: int, group_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, group_id, group_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    group_id = excluded.group_id,
                    group_name = excluded.group_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, group_id, group_name),
            )
            await db.commit()
        # Очищаем кеш для этого пользователя
        await clear_cache(f"get_user_data:{user_id}")

    @cached(ttl=1800)  # 30 минут для данных пользователя
    async def get_user_data(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT group_id, group_name FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {"group_id": row[0], "group_name": row[1]}
                return None
