import datetime
import functools
import logging
import os
import threading
import time
from typing import Any, Callable

from utils.command import CommandExecutor
from utils.response import Result


logger = logging.getLogger()

__all__ = [
    "timer",
    "exception",
    "execute",
]


def timer(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrap(self, *args, **kwargs):
        start_time = time.time()
        logger.debug("Task start(%s): %s, %s", fn.__name__, start_time, datetime.datetime.now())
        result = fn(self, *args, **kwargs)
        cost_seconds = time.time() - start_time
        logger.info(
            f"Process: %s, Thread: %s, <Task (%s) finished!!!>. Time cost: %s(s), %s",
            os.getpid(),
            threading.current_thread().name,
            fn.__name__,
            cost_seconds,
            datetime.timedelta(seconds=cost_seconds),
        )
        return result

    return wrap


class exception:

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, *args: Any, **kwargs: Any):
        try:
            data = self.fn(*args, **kwargs)
            result = Result(0, data=data)
            return result
        except KeyboardInterrupt as err:
            logger.exception(err)
            result = Result(601, msg=err)
            return result
        except Exception as err:
            logger.exception(err)
            media = getattr(self.fn, '__self__', None)
            data = {"media": media} if media else None
            result = Result(1, data=data, msg=str(err))
            return result

    def __get__(self, obj, obj_type):
        return functools.partial(self.__call__, obj)


def execute(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrap(self, *args, **kwargs):
        media, command, new_file_path = fn(self, *args, **kwargs)
        result = CommandExecutor.run(command, getattr(self, "monitor", None))
        return {
            "media": media,
            "new_file_path": new_file_path,
            "result": result,
        }

    return wrap



