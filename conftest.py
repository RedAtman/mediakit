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


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """每个测试都在空配置目录下跑, 看不见开发者自己的 ~/.config/mediakit.

    Root cause: 一旦机器上存在 ~/.config/mediakit/config.toml (以及 .env 里的
    WATCH_FOLDER_FILE), watcher 的测试就会读到真实配置, 断言里突然出现用户自己的
    325 个下载目录. 与 isolated_sqlite 同一个道理: 机器状态不能渗进测试.
    """
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg-config'))
    monkeypatch.delenv('MEDIAKIT_CONFIG', raising=False)
    monkeypatch.delenv('WATCH_FOLDER_FILE', raising=False)


@pytest.fixture(autouse=True)
def isolated_pid_dir(tmp_path, monkeypatch):
    """每个测试用自己的 pid 目录.

    Root cause: watcher 的 core() 测试会走到 _write_pid_file()/_cleanup_pid_file(),
    于是整个测试套件在 ~/.mediakit/daemon.pid 上又写又删 —— 守护进程运行时跑一次测试,
    它的 pid 文件就没了, `mediakit stop` 和单实例守卫随之失效.
    """
    monkeypatch.setenv('MEDIAKIT_PID_DIR', str(tmp_path / 'mediakit-pid'))
