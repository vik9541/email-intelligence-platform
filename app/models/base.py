"""
Базовые модели и настройки SQLAlchemy.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех ORM моделей."""
    pass
