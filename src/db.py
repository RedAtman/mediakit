from functools import cache

from config import CONFIG
from utils.db import _sqlalchemy, base


__all__ = [
    "DatabaseEngine",
]


class DatabaseEngine:
    _DB_ENGINE_CLS = _sqlalchemy.Engine

    @classmethod
    @cache
    def engine(cls) -> base.BaseEngine:
        engine = cls._DB_ENGINE_CLS(CONFIG.SQLITE_DATABASE)
        engine.create_db_and_tables()
        return engine

    @classmethod
    def get_engine(cls, engine: base.BaseEngine | None = None) -> base.BaseEngine:
        if engine is not None:
            return engine
        return cls.engine
