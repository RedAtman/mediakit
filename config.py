import json
import os
import sys
from importlib import import_module


def load_env():
    from dotenv import load_dotenv

    load_dotenv()


try:
    load_env()
except ImportError:
    import subprocess

    subprocess.run(['pip', 'install', 'python-dotenv'], check=True)
    load_env()

__all__ = ['CONFIG']


class _BaseConfig:
    # All subclasses of BaseConfig will be added to this mapping.
    mapping: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.mapping[cls.__name__.lower()] = cls

    DEBUG = False
    TESTING = False
    # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, BASE_DIR)
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

    PROJECT_NAME = 'mediakit'
    PROJECT_VERSION = '0.0.1'
    PROJECT_DESCRIPTION = 'MediaKit is a media processing toolkit that provides a unified interface for various media-related tasks, including compression, trimming, scaling, format conversion, and metadata management. It is designed to be extensible and adaptable to different media processing needs.'
    # PROJECT_AUTHOR = 'mediakit'

    # CPU throttling default limit
    CPU_LIMIT: int = int(os.getenv('CPU_LIMIT', '100'))

    # SQLITE
    SQLITE_DATABASE = os.getenv('SQLITE_DATABASE', os.path.join(BASE_DIR, 'db.db'))
    SQLITE_CONNECTION_POOL_SIZE = int(os.getenv('SQLITE_CONNECTION_POOL_SIZE', 10))

    # FFMPEG
    FFMPEG_BIN_DIR = os.getenv('FFMPEG_BIN_DIR', '/opt/homebrew/bin/ffmpeg')
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', 1))

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
    WATCH_FOLDER_FILE: str = os.path.join(os.path.dirname(__file__), 'var', 'folder.sh')

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


import_module('utils.logger.init')
