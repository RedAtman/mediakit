import functools
import os
from re import L
import threading
import time
from typing import Any, Callable, List, Type

from base.media import BaseMedia
from logger import logger

__all__ = [
    'timer',
    'execute_shell_command',
    'class_property',
]


def timer(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrap(self, *args, **kwargs):
        start_time = time.time()
        logger.debug('Task start(%s): %s', fn.__name__, start_time)
        result = fn(self, *args, **kwargs)
        logger.info(
            'Process: %s, Thread: %s, <Task (%s) finished!!!>. Time cost: %s',
            os.getpid(),
            threading.current_thread().name,
            fn.__name__,
            time.time() - start_time,
        )
        return result
    return wrap


def execute_shell_command(fn: Callable):
    @functools.wraps(fn)
    def wrap(self: Type[BaseMedia], *args, **kwargs):
        # Call the original function to get the shell command
        command: List[str]
        new_file_path: str
        command, new_file_path = fn(self, *args, **kwargs)
        logger.debug('self: %s, command: %s', self, command)
        self.executor.run(command)
        return self.__class__(new_file_path)
    return wrap


class class_property:   # pylint: disable=invalid-name
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)



# class class_property:
#     """Class property decorator.

#     Example:
#         class A:
#             @class_property
#             def x(cls):
#                 return 1
#     """
#     def __init__(self, method=None):
#         self.fget = method

#     def __get__(self, instance, cls=None):
#         return self.fget(cls)

#     def getter(self, method):
#         self.fget = method
#         return self
