from datetime import datetime

from sqlalchemy import Integer, String, TIMESTAMP, func
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase, Mapped


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False)
    group_name: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
