from sqlalchemy.orm import DeclarativeBase, AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass