from datetime import datetime
import functools
import json
import os
from typing import Any, Dict, List

from base.video import Video
from config import CONFIG
from logger import logger
from utils import Dict2Obj, calculate_md5, db, decorator, exceptions

__all__ = [
    'BaseFolder',
]


class BaseFolder:
    MEDIA_CLS = Video

    def __init__(self, path: str):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found at path: {path}')
        if not os.path.isdir(rf'{path}'):
            raise TypeError(f'Path is not a folder: {path}')
        self.path = path

    @property
    def meta(self):
        return Dict2Obj(self.read_meta(self.path))

    @staticmethod
    def read_meta(path: str) -> Dict[str, str]:
        '''Read media meta from meta.json under the folder.

        Arguments:
            path {str} -- [folder path]

        Returns:
            [dict] -- [media meta]
            e.g.: {
                "video": {
                    "path": "20210831_ProRes-444_BT2020L_OriRes_25_UHQ_mb05.mov",
                    "title": "20210831_中国北京天坛祈年殿",
                    "artist": "aQuantum,一枚量子",
                    "category": "time_lapse",
                    "camera": "sony_a7r2",
                    "lens": "laowa_12mm_f2.8",
                    "keywords": "天坛,祈年殿,北京,中国,中国北京,中国"
                },
                "resolution": "4k",
                "reverse": False,
                "crop": {
                    "w": 4096,
                    "h": 2160,
                    "x": 0,
                    "y": 100
                },
                "audio": {
                    "path": "/Users/nut/Downloads/Illuminate (Trailer Music) - Dirk Leupolz.mp3",
                    "defer": 15.3,
                    "fade_duration": 1
                },
                "watermark": {
                    "path": "/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png",
                    "transparent": 0.3
                }
            }
        '''
        if not os.listdir(path).count('meta.json'):
            raise FileNotFoundError(f'File not found: {path}/meta.json')
        try:
            with open(os.path.join(path, 'meta.json'), 'r', encoding='utf-8') as fd:
                content = fd.read()
                meta = json.loads(content).get('video', {})
                return meta
        except Exception as err:
            logger.exception(err)
            raise err

    @functools.cached_property
    def files(self):
        return self.get_files(self.path)

    @functools.cached_property
    def medias(self):
        return self.get_medias(self.path)

    @staticmethod
    def get_files(path: str):
        return (os.path.abspath(os.path.join(path, file)) for file in os.listdir(path))

    @classmethod
    def get_medias(cls, path: str):
        for file in cls.get_files(path):
            try:
                media = cls.MEDIA_CLS(file)
                yield media
            except exceptions.NotMediaException:
                continue
            except Exception as err:
                logger.exception(err)
                continue

    @decorator.timer
    def get_texts(self):
        return (self.MEDIA_CLS(file).speech_to_text() for file in self.files)

    def save_texts(self, ext='txt'):
        '''Save media text to file.

        Arguments:
            ext {str} -- [file extension]

        Returns:
            [None] -- [None]
        '''
        return {media.path: media.save_text(ext=ext) for media in self.medias}
        # try:
        #     while True:
        #         media = next(self.medias)
        #         media.save_text(ext=ext)
        #         # break
        # except StopIteration:
        #     logger.info("All media have been processed.")
        #     return None
        # except Exception as err:
        #     logger.exception(err)
        #     raise err

    def convert_format(self, ext='mp4'):
        '''Convert media format.

        Keyword Arguments:
            ext {str} -- [output file extension] (default: {'mp4'})

        Returns:
            [dict] -- [media info]
        '''
        return {media.path: media.convert_format(ext=ext) for media in self.medias}

    @classmethod
    @property
    @functools.cache
    def db(cls) -> db.SQLiteDB:
        '''Get db.

        Returns:
            [SQLiteDB] -- [SQLiteDB instance]
        '''
        return db.SQLiteDB(CONFIG.SQLITE_DATABASE)

    def scan(self):
        '''Scan media.

        Returns:
            [list] -- [SQL execute result]
        '''
        return self._scan(self.path)

    @classmethod
    def _scan(cls, path: str=CONFIG.MEDIA_FILE_FOLDER):
        cls.db.execute_query(
            "CREATE TABLE IF NOT EXISTS media (title TEXT UNIQUE, \
                md5 TEXT NOT NULL UNIQUE, dirname TEXT, created_date TIMESTAMP, finished_date TIMESTAMP)"
        )
        result_list: List[Any] = []
        for media in cls.get_medias(path):
            md5 = calculate_md5(media.path)
            result = cls.db.execute_insert_update_delete(
                "INSERT OR IGNORE INTO media (title, md5, dirname, created_date) VALUES (?, ?, ?, ?)",
                (media.title, md5, media.dirname, datetime.now()),
            )
            result_list.append(result)
        return result_list

    def unfinished(self):
        '''Scan unfinished media.

        Returns:
            [list] -- [media info]
        '''
        return self._unfinished()

    @classmethod
    def _unfinished(cls):
        return cls.db.execute_query("SELECT * FROM media WHERE finished_date IS NULL")
