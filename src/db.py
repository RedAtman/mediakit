import functools

from config import CONFIG
from utils.db import _sqlalchemy, base


__all__ = [
    "DatabaseEngine",
]


class DatabaseEngine:
    _DB_ENGINE_CLS = _sqlalchemy.Engine

    @classmethod
    @property
    @functools.cache
    def engine(cls) -> base.BaseEngine:
        return cls._DB_ENGINE_CLS(CONFIG.SQLITE_DATABASE)
