import logging
import os
from typing import Any, Callable


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# class _ColorfulFormatter(logging.Formatter):

#     def __init__(self, *args, **kwargs):
#         self._root_name = kwargs.pop("root_name") + "."
#         self._abbrev_name = kwargs.pop("abbrev_name", "")
#         if len(self._abbrev_name):
#             self._abbrev_name = self._abbrev_name + "."
#         super(_ColorfulFormatter, self).__init__(*args, **kwargs)

#     def formatMessage(self, record):
#         record.name = record.name.replace(self._root_name, self._abbrev_name)
#         log = super(_ColorfulFormatter, self).formatMessage(record)
#         if record.levelno == logging.WARNING:
#             prefix = colored("WARNING", "red", attrs=["blink"])
#         elif record.levelno == logging.ERROR or record.levelno == logging.CRITICAL:
#             prefix = colored("ERROR", "red", attrs=["blink", "underline"])
#         else:
#             return log
#         return prefix + " " + log


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


class LevelColorFilter(logging.Filter):

    def filter(self, record: logging.LogRecord):
        super().filter(record)
        if self.__class__.__name__.upper().startswith(record.levelname):
            return True
        return False


class RelativePathFormatter(logging.Formatter):

    def format(self, record) -> str:
        record.relpath = record.pathname.replace(f"{BASE_DIR}/", "", 1)
        return super().format(record)


from enum import Enum


class ColorFormatter(logging.Formatter):

    PREFIX = "\033["
    SUFFIX = "\033[0m"

    class Color(Enum):
        DEFAULT = 29
        GREY = 30  # 灰色
        RED = 31  # 红色
        GREEN = 32  # 绿色
        YELLOW = 33  # 黄色
        BLUE = 34  # 蓝色
        MAGENTA = 35  # 紫色
        CYAN = 36  # 青色
        WHITE = 37  # 白色

    COLOR_MAPPING = {
        logging.DEBUG: Color.CYAN.value,
        logging.INFO: Color.GREEN.value,
        logging.WARNING: Color.YELLOW.value,
        logging.ERROR: Color.RED.value,
        logging.CRITICAL: Color.MAGENTA.value,
    }

    # _format = f"[%(levelname)s]: {ColorFormatter.PREFIX}"
    #         f"{ColorFormatter.Color.GREY.value}m%(pathname)s:%(lineno)d:"
    #         f"{ColorFormatter.SUFFIX} %(funcName)s: %(message)s",
    # format_str = f"[%(levelname)s]:{PREFIX} {Color.GREY.value}m%(pathname)s:%(lineno)d: \
    #     {SUFFIX} %(funcName)s: %(message)s"
    format_str = f"[%(levelname)s]:%(pathname)s:%(lineno)d: %(funcName)s: %(message)s"

    @classmethod
    def _wrap_with(cls, color_code):
        def inner(text, bold=False):
            c = color_code
            if bold:
                c = f"1;{c}"
            return f"{cls.PREFIX}{c}m{text}{cls.SUFFIX}"

        return inner

    def format(self, record: logging.LogRecord) -> str:
        # print("record", record.__dict__)
        level_color = self.COLOR_MAPPING.get(record.levelno, self.Color.WHITE.value)
        level_name = logging.getLevelName(record.levelno)
        record.levelname = f"{self.PREFIX}{level_color}m{level_name}{self.SUFFIX}"
        record.pathname = (
            f"{self.PREFIX}{self.Color.GREY.value}m{record.pathname}{self.SUFFIX}"
        )
        # record.lineno = f"{self.PREFIX}{self.Color.GREY.value}m{record.lineno}{self.SUFFIX}"
        record.msg = f"{self.PREFIX}{level_color}m{record.msg}{self.SUFFIX}"
        return super().format(record)


import functools
from pprint import pformat
import sys

from pygments import formatters, highlight, lexers


def json_wrap(fuc):
    @functools.wraps(fuc)
    def inner(self, msg, *args, **kwargs):
        # Get the previous frame in the stack, which is the caller of this function.
        frame = sys._getframe(0)
        f = frame.f_code.co_filename
        while frame and frame.f_code.co_filename == f:
            frame = frame.f_back
        filename = frame.f_code.co_filename  # type: ignore
        lineno = frame.f_lineno  # type: ignore
        name = frame.f_code.co_name  # type: ignore

        # Print the stack trace
        BOLD = "\033[1m"
        GRAY = "\033[90m"
        WARNING = "\033[93m"
        END = "\033[0m"
        print(f"[{BOLD}{WARNING}JSON{END}]: {GRAY}{filename}:{lineno}: {name}{END}")

        # Print incoming message.
        print(
            highlight(
                pformat(msg, indent=1, width=80, depth=9),
                lexers.JsonnetLexer(),
                # lexers.JsonLexer(),
                # lexers.PythonTracebackLexer(),
                formatters.TerminalTrueColorFormatter(
                    style="algol",
                    # style='dracula',
                    # style='friendly',
                    # style='github-dark',
                    # style='gruvbox-dark',
                    # style='gruvbox-light',
                    # style='native',
                    # style='rrt',
                    # style='stata-light',
                    # style='tango',
                    # style='trac',
                    # style='xcode',
                ),
                # formatters.TerminalFormatter(),
                # formatters.Terminal256Formatter(bg='dark', colorscheme='colorful'),
                # formatters.TerminalFormatter(bg='dark'),
                # formatters.TerminalFormatter(bg='light'),
            ),
            # end='',
        )

    return inner


class _Logger(logging.Logger):
    """Add json type hit to logger."""

    json: Callable[..., Any]


setattr(logging.Logger, "json", json_wrap(getattr(logging.Logger, "debug")))


if __name__ == "__main__":
    import logging.config

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "color": {
                "()": ColorFormatter,
                "format": ColorFormatter.format_str,
            },
            "relative": {
                "()": RelativePathFormatter,
                "format": "%(relpath)s:%(lineno)d: %(funcName)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "color",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": "DEBUG",
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(LOGGING_CONFIG)
    logger: _Logger = logging.getLogger(__name__)  # type: ignore
    # logger.setLevel(logging.WARNING)
    logger.debug("log level: debug")
    logger.info("log level: info")
    logger.warning("log level: warning")
    logger.error("log level: error")
    logger.exception("log level: exception")
    logger.critical("log level: critical")
    logger.json({"a": 1, "b": "-" * 80, "c": {"d": 3, "e": 4, "f": {"g": 5, "h": 6}}})

    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    logger.json(sqlalchemy_logger.__dict__)
    sqlalchemy_logger.debug("sqlalchemy debug")
    sqlalchemy_logger.info("sqlalchemy info")
    sqlalchemy_logger.warning("sqlalchemy warning")
