from importlib import import_module
import json
import os
import sys


def load_env():
    from dotenv import find_dotenv, load_dotenv

    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path)
        return
    load_dotenv(os.path.join(os.path.expanduser('~'), '.env'))


try:
    load_env()
except ImportError:
    import subprocess

    subprocess.run(['pip', 'install', 'python-dotenv'], check=True)
    load_env()

__all__ = ['CONFIG']


def frozen_state_dir(system: str, home: str, localappdata: str = '') -> str:
    """冻结构建 (brew / 单文件二进制) 的状态目录.

    不能落在可执行文件旁边: brew 装进 Cellar, `brew upgrade` 会整个替换版本目录,
    logs/ 和 db.db 会随之消失; 而且 Cellar 本不应被程序写入.
    """
    if system == 'darwin':
        return os.path.join(home, 'Library', 'Application Support', 'mediakit')
    if system == 'win32':
        local = localappdata or os.path.join(home, 'AppData', 'Local')
        return os.path.join(local, 'mediakit')
    return os.path.join(home, '.local', 'state', 'mediakit')


class _BaseConfig:
    # All subclasses of BaseConfig will be added to this mapping.
    mapping: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.mapping[cls.__name__.lower()] = cls

    DEBUG = False
    TESTING = False
    # PyInstaller onefile 下 __file__ 指向临时解包目录 (_MEIPASS), 退出即删,
    # 所以冻结时 BASE_DIR 随可执行文件走; 但运行期状态 (db.db / logs) 放到
    # 平台状态目录, 否则 brew upgrade 换版本目录时会丢.
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
        STATE_DIR = frozen_state_dir(sys.platform, os.path.expanduser('~'), os.getenv('LOCALAPPDATA') or '')
    else:
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        STATE_DIR = BASE_DIR
    sys.path.insert(0, BASE_DIR)
    LOG_DIR = os.path.join(STATE_DIR, 'logs')
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

    PROJECT_NAME = 'mediakit'
    PROJECT_DESCRIPTION = 'MediaKit is a media processing toolkit that provides a unified interface for various media-related tasks, including compression, trimming, scaling, format conversion, and metadata management. It is designed to be extensible and adaptable to different media processing needs.'
    # PROJECT_AUTHOR = 'mediakit'

    # CPU throttling default limit
    CPU_LIMIT: int = int(os.getenv('CPU_LIMIT', '100'))

    # SQLITE
    SQLITE_DATABASE = os.path.abspath(os.path.join(STATE_DIR, os.getenv('SQLITE_DATABASE') or 'db.db'))
    SQLITE_CONNECTION_POOL_SIZE = int(os.getenv('SQLITE_CONNECTION_POOL_SIZE', 10))

    # FFMPEG
    FFMPEG_BIN_DIR = os.getenv('FFMPEG_BIN_DIR', '')
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', 1))
    # compress 兜底参数: CLI 未显式指定 --resolution / --fps 时使用
    COMPRESS_RESOLUTION = os.getenv('COMPRESS_RESOLUTION', 'HD')
    COMPRESS_FPS = int(os.getenv('COMPRESS_FPS', '24'))

    # BAIDU_TRANSLATE
    BAIDU_TRANSLATE_API = os.getenv('BAIDU_TRANSLATE_API', '')
    BAIDU_TRANSLATE_APP_ID = os.getenv('BAIDU_TRANSLATE_APP_ID', '')
    BAIDU_TRANSLATE_SECRET_KEY = os.getenv('BAIDU_TRANSLATE_SECRET_KEY', '')
    BAIDU_TRANSLATE_SALT = os.getenv('BAIDU_TRANSLATE_SALT', '')

    # MEDIA METADATA
    ARTIST = os.getenv('ARTIST', 'media_helper').split(',')
    CATEGORY = json.loads(os.getenv('CATEGORY', '{}'))
    CAMERA = json.loads(os.getenv('CAMERA', '{}'))
    LENS = json.loads(os.getenv('LENS', '{}'))

    # MEDIA FILE
    MEDIA_FILE_PATH = os.getenv('MEDIA_FILE_PATH', 'samples/zh.mp4')
    MEDIA_FILE_FOLDER: str = os.getenv('MEDIA_FILE_FOLDER', 'samples')
    WATCH_FOLDER_FILE: str = os.getenv('WATCH_FOLDER_FILE', 'var/folder.sh')

    # TRANSCRIBER
    TRANSCRIBER_MODEL = os.getenv('TRANSCRIBER_MODEL', 'base')
    TRANSCRIBER_INITIAL_PROMPT = os.getenv(
        'TRANSCRIBER_INITIAL_PROMPT',
        """
        Coincident Indicators:
        1. Core Outputs and Revenues.
        2. Consumption and Trade.
        """,
    )

    # LLAMA
    LLAMA_MODEL = os.getenv('LLAMA_MODEL', 'base')


class Development(_BaseConfig):
    """Development environment configuration"""

    DEBUG = True


class Testing(_BaseConfig):
    """Testing environment configuration"""

    TESTING = True


class Production(_BaseConfig):
    """Production environment configuration"""

    # LOG_LEVEL = "WARNING"
    pass


env: str = os.getenv('ENV', 'development')
CONFIG: type[_BaseConfig] = _BaseConfig.mapping.get(env, Development)

# utils.logger.init 优先读 env BASE_DIR; 指向 STATE_DIR 以便日志与 db.db 同处
os.environ.setdefault('BASE_DIR', _BaseConfig.STATE_DIR)

import_module('utils.logger.init')
