import json
import os

from logger import logger
from utils import Dict2Obj


class Audio:
    '''docstring for Audio'''

    def __init__(self, cls):
        # self.arg = arg
        print('cls', type(cls), cls)

    @classmethod
    def trim(cls):
        command = 'ffmpeg -y -i /Users/nut/Downloads/Father.m4a -c copy -ss 00:02:43.00 -to 00:51:56 output.m4a'.strip()
        return command


class MediaTool:
    '''Processing media files based on meta.json'''

    def __init__(self, directory):
        self.directory = directory.strip()
        self._meta = self.read_meta_json(directory)
        self.meta = Dict2Obj(self._meta)

    # @decorator.class_property
    # def meta(cls):
    #     self.read_meta_json(directory)

    @staticmethod
    def read_meta_json(path):
        '''读取指定dir下面meta.json文件的信息

        Arguments:
            path {str} -- [文件夹地址]

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
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'Path not found: {path}')
        if not os.path.isdir(path):
            raise NotADirectoryError(f'Not a directory: {path}')
        if not os.listdir(path).count('meta.json'):
            raise FileNotFoundError(f'File not found: {path}/meta.json')
        try:
            with open(os.path.join(path, 'meta.json'), 'r', encoding='utf-8') as fd:
                meta = json.loads(fd.read()).get('video', {})
        except Exception as err:
            logger.exception(err)
            raise err
        return meta

    def combine(self, ):
        media = Media(**self.meta.video.__dict__)
        return media.combine(
            watermark_path=self.meta.watermark.path,
            watermark_transparent=self.meta.watermark.transparent,
            audio_path=self.meta.audio.path,
            audio_defer=self.meta.audio.defer,
            fade_duration=self.meta.audio.fade_duration,
            crop=self.meta.resolution,
            crop_y=self.meta.crop.y,
            reverse=self.meta.reverse,
        )

    def trim(self, time=()):
        media = Media(**self.meta.video.__dict__)
        return media.trim(time=time)
