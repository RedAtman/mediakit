import functools
import os
import threading
import time

from logger import logger

__all__ = [
    'timer',
    'execute_shell_command',
    'class_property',
]


def timer(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        start_time = time.time()
        logger.debug('Task start(%s): %s', func.__name__, start_time)
        result = func(self, *args, **kwargs)
        logger.info(
            'Process: %s, Thread: %s, <Task (%s) finished!!!>. Time cost: %s',
            os.getpid(),
            threading.current_thread().name,
            func.__name__,
            time.time() - start_time,
        )
        return result
    return wrap


def execute_shell_command(func):
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        # Call the original function to get the shell command
        command, new_file_path = func(self, *args, **kwargs)
        logger.debug('self: %s, command: %s', self, command)
        self.executor.run(command)
        return self.__class__(new_file_path)
    return wrap


class class_property:   # pylint: disable=invalid-name
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)
