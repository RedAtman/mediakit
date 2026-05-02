from functools import cache

from config import CONFIG
from utils.db import _sqlalchemy, base


__all__ = [
    "DatabaseEngine",
]


class DatabaseEngine:
    _DB_ENGINE_CLS = _sqlalchemy.Engine

    @classmethod
    @property
    @cache
    def engine(cls) -> base.BaseEngine:
        return cls._DB_ENGINE_CLS(CONFIG.SQLITE_DATABASE)

    @classmethod
    def get_engine(cls, engine: base.BaseEngine | None = None) -> base.BaseEngine:
        if engine is not None:
            return engine
        return cls.engine
