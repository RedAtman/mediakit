import functools
import time
from utils import log


def timekeep(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        start_time = time.time()
        ret = func(*args, **kwargs)
        log.info("耗时:", time.time() - start_time, '执行结果:', ret)
        return ret
    return inner


def Timekeep():
    """
    用于类方法(可调用self)的装饰器
    """
    def wrap(func):
        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            start_time = time.time()
            log.debug('Task start(%s):' % (func.__name__), start_time)
            ret = func(self, *args, **kwargs)
            log.info('耗时:', time.time() - start_time, '执行结果:', ret)
            return ret
        return inner
    return wrap
