
# import sys
# import traceback

from logger import logger

__all__ = ['UnknownCodeException', 'NotMediaException', ]


class UnknownCodeException(Exception):
    def __init__(self, code, exception_cls, mapper__code_msg):
        self.code = code
        self.exception_cls = exception_cls
        self.mapper__code_msg = mapper__code_msg

    def __str__(self):
        msg = f'Unknown code: {self.code} in {self.exception_cls}. Available codes: {self.mapper__code_msg.keys()}'
        logger.error(msg)
        return msg


class _BaseException(Exception):

    mapper__code_msg = {}

    def __init__(self, code, msg=None):
        ''''''
        if code not in self.mapper__code_msg:
            # logger.error(sys._getframe().f_back.f_code.co_name)
            raise UnknownCodeException(code, self.__class__.__name__, self.mapper__code_msg)
        self.code = code
        self.msg = msg or self.mapper__code_msg.get(code, '')


class NotMediaException(_BaseException):
    mapper__code_msg = {
        101: 'Not a media file.',
    }



if __name__ == '__main__':
    ape = NotMediaException(101)
    print(ape)
    print(ape.code)
    print(ape.msg)
    print(ape.__dict__)
