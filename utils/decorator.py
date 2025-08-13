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
    "class_property",
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
            result = Result(1, err)
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


class class_property:
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner) -> Any:
        return self.f(owner)


# class class_property:
#     """Class property decorator.

#     e.g.
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


# classproperty = type(
#     'classproperty',
#     (property, ),
#     {
#         '__get__': lambda self, cls, owner: self.fget.__get__(None, owner)()
#     }
# )


def singleton(cls: type[Any]):
    _mapper_cls_instance: dict[Any, Any] = {}

    @functools.wraps(cls)
    def instance(*args, **kwargs):
        if cls not in _mapper_cls_instance:
            _mapper_cls_instance[cls] = cls(*args, **kwargs)
        return _mapper_cls_instance[cls]

    return instance


if __name__ == "__main__":

    class A:

        @class_property
        def attr(cls):
            print("class_property", cls, type(cls))
            return 1

    a = A()
    print(a.attr)
    print(A.attr)
    print(a.attr == A.attr)

    @singleton
    class B:
        def __init__(self, name):
            self.name = name

    b1 = B("b1")
    b2 = B("b2")
    print(b1.name, b2.name)
    print(b1 is b2)
