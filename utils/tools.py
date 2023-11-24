import mimetypes

from logger import logger

__all__ = ['Dict2Obj', 'is_media',]


class Dict2Obj:
    '''Convert dict to object recursively.'''
    def __init__(self, data):
        for name, value in data.items():
            setattr(self, name, self.__wrap(value))

    def __wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self.__wrap(v) for v in value])
        return Dict2Obj(value) if isinstance(value, dict) else value

    def _dict(self):
        return {k: v._dict() if isinstance(v, Dict2Obj) else v
                for k, v in self.__dict__.items()}


# class Dict2Obj(dict):
#     def __init__(self, *args, **kwargs):
#         super(Dict2Obj, self).__init__(*args, **kwargs)
#         self.__dict__ = self

#     def _dict(self):
#         return dict(self)


mimetypes.init()


def is_media(file):
    '''Check if the file is a media file.'''
    mime_start = mimetypes.guess_type(file)[0]
    if mime_start is not None:
        mime_start = mime_start.split('/')[0]
        if mime_start in ['audio', 'video', ]:
            return True
    return False



if __name__ == '__main__':
    _meta = {
        "video": {
            "path": "20210831_ProRes-444_BT2020L_OriRes_25_UHQ_mb05.mov",
            "title": "20210831_中国北京天坛祈年殿",
            "artist": "aQuantum,一枚量子",
            "category": "time_lapse",
            "camera": "sony_α7r2",
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
    meta = Dict2Obj(_meta)
    logger.info((type(meta), meta))
    logger.info((type(meta._dict()), meta._dict()))
    logger.info((type(meta.video), meta.video))
    logger.info((type(meta.video._dict()), meta.video._dict()))
    logger.info((type(meta.video.path), meta.video.path))
