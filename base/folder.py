import functools
import json
import os

from base.video import Video
from logger import logger
from utils import Dict2Obj, decorator, exceptions

__all__ = [
    'BaseFolder',
]


class BaseFolder:
    MEDIA_CLS = Video

    def __init__(self, path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found at path: {path}')
        if not os.path.isdir(rf'{path}'):
            raise TypeError(f'Path is not a folder: {path}')
        self.path = path

    @functools.cached_property
    def files(self):
        return self.get_files(self.path)

    @functools.cached_property
    def medias(self):
        return self.get_medias(self.path)

    @classmethod
    def get_files(cls, path):
        return (os.path.abspath(os.path.join(path, file)) for file in os.listdir(path))

    @classmethod
    def get_medias(cls, path):
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
        try:
            while True:
                media = next(self.medias)
                media.save_text(ext=ext)
                # break
        except StopIteration:
            logger.info("All media have been processed.")
        # return 'Done'
