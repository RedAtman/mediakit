import pytest

from config import CONFIG
from src.db import DatabaseEngine

# DatabaseEngine.engine 是 @classmethod + @cache, 取出被缓存的原始函数以便清缓存.
# 直接 clear 而不是替换 DatabaseEngine.engine: SqlAlchemyFolderMixin.engine 在
# class 定义时就绑定了这个 classmethod, 只有共享同一份 cache 才能一起生效.
_cached_engine = DatabaseEngine.__dict__['engine'].__func__


@pytest.fixture(autouse=True)
def isolated_sqlite(tmp_path, monkeypatch):
    """每个测试都用 tmp_path 下的独立 sqlite 库.

    Root cause: tests reached CONFIG.SQLITE_DATABASE directly, i.e. the repo's
    real db.db (4499 rows of the user's data). That both dirtied live data and
    produced bogus UNIQUE conflicts whenever a hardcoded md5 happened to exist.
    """
    monkeypatch.setattr(CONFIG, 'SQLITE_DATABASE', str(tmp_path / 'test.db'))
    _cached_engine.cache_clear()
    yield
    _cached_engine.cache_clear()
