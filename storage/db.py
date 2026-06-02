from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from storage.cache import cached, clear_cache
from storage.models import Base, User


class Database:
    def __init__(self, url: str = "sqlite+aiosqlite:///storage.db"):
        self.url = url
        self.engine = create_async_engine(url=url)
        self.sessionmaker = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def set_user_group(self, user_id: int, group_id: int, group_name: str):
        async with self.sessionmaker() as session:
            async with session.begin():
                user = await session.get(User, user_id)
                if user:
                    user.group_id = group_id
                    user.group_name = group_name
                else:
                    new_user = User(user_id=user_id, group_id=group_id, group_name=group_name)
                    session.add(new_user)
        await clear_cache(f"get_user_data:{user_id}")

    @cached(ttl=1800)
    async def get_user_data(self, user_id: int) -> dict | None:
        async with self.sessionmaker() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None
            return {"group_id": user.group_id, "group_name": user.group_name}
