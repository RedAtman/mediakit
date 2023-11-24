import os
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# from logger import logger

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    # All subclasses of BaseConfig will be added to this mapping.
    mapping = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.mapping[cls.__name__.lower()] = cls

    DEBUG = False
    TESTING = False
    BASE_DIR = BASE_DIR
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

    PROJECT_NAME = 'media_handler'
    PROJECT_VERSION = '0.0.1'
    PROJECT_DESCRIPTION = 'Media Handler'
    # PROJECT_AUTHOR = 'media_handler'

    # BAIDU_TRANSLATE
    BAIDU_TRANSLATE_API = os.getenv('BAIDU_TRANSLATE_API')
    BAIDU_TRANSLATE_APP_ID = os.getenv('BAIDU_TRANSLATE_APP_ID')
    BAIDU_TRANSLATE_SECRET_KEY = os.getenv('BAIDU_TRANSLATE_SECRET_KEY')
    BAIDU_TRANSLATE_SALT = os.getenv('BAIDU_TRANSLATE_SALT')

    # MEDIA METADATA
    ARTIST = os.getenv('ARTIST', 'media_helper').split(',')
    CATEGORY = json.loads(os.getenv('CATEGORY', '{}'))
    CAMERA = json.loads(os.getenv('CAMERA', '{}'))
    LENS = json.loads(os.getenv('LENS', '{}'))

    # MEDIA FILE
    MEDIA_FILE_PATH = os.getenv('MEDIA_FILE_PATH', '~/Documents/tmp/test.mp4')
    MEDIA_FILE_DIRECTORY = os.getenv('MEDIA_FILE_DIRECTORY', '~/Documents/tmp')


class Development(BaseConfig):
    '''Development environment configuration'''
    DEBUG = True


class Testing(BaseConfig):
    '''Testing environment configuration'''
    TESTING = True


class Production(BaseConfig):
    '''Production environment configuration'''
    LOG_LEVEL = 'WARNING'


config = BaseConfig.mapping.get(os.getenv('ENV', 'development'), Development)
