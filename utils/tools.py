import sys


# import mimetypes
# from typing import List


__all__ = [
    "Dict2Obj",
]


# class Dict2Obj:
#     '''Convert dict to object recursively.'''
#     def __init__(self, data):
#         for name, value in data.items():
#             setattr(self, name, self.__wrap(value))

#     def __wrap(self, value):
#         if isinstance(value, (tuple, list, set, frozenset)):
#             return type(value)([self.__wrap(v) for v in value])
#         return Dict2Obj(value) if isinstance(value, dict) else value

#     def _dict(self):
#         return {k: v._dict() if isinstance(v, Dict2Obj) else v
#                 for k, v in self.__dict__.items()}


class Dict2Obj(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self


# mimetypes.init()


# def is_media(file: str, include_type: List[str] = ["image", "audio", "video"]):
#     """Check if the file is a media file."""
#     mime_start = mimetypes.guess_type(file)[0]
#     if mime_start is not None:
#         mime_start = mime_start.split("/")[0]
#         if mime_start in include_type:
#             return True
#     return False



