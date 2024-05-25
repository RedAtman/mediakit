import logging
import os
import sys


# class RelativePathFilter(logging.Filter):
#     def filter(self, record: logging.LogRecord):
#         record.relpath = record.pathname.replace(f'{BASE_DIR}/', '', 1)
#         return True


class RelativePathFilter(logging.Filter):

    def filter(self, record):
        pathname = record.pathname
        record.relativepath = None
        abs_sys_paths = map(os.path.abspath, sys.path)
        for path in sorted(abs_sys_paths, key=len, reverse=True):
            if not path.endswith(os.sep):
                path += os.sep
            if pathname.startswith(path):
                record.relativepath = os.path.relpath(pathname, path)
                break
        return super().filter(record)


class RelPathFilter(logging.Filter):

    def filter(self, record):
        record.relpath = os.path.relpath(record.pathname)
        return super().filter(record)


class LevelColorFilter(logging.Filter):

    def filter(self, record: logging.LogRecord):
        super().filter(record)
        if self.__class__.__name__.upper().startswith(record.levelname):
            return True
        return False
