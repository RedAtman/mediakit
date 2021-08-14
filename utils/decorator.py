import functools
import time
# import sys
import os
import copy
import threading
import subprocess
from utils import log


def timekeep(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        start_time = time.time()
        ret = func(*args, **kwargs)
        log.warning('线程:%s, 父进程:%s, 耗时:%s, <Task (%s) finished!!!>' % (
            threading.current_thread().getName(), os.getpid(), time.time() - start_time, func.__name__))
        return ret
    return inner


def Timekeep():
    """
    用于类方法(可调用self)的装饰器
    """
    def wrapper(func):
        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            start_time = time.time()
            log.debug('Task start(%s):' % (func.__name__), start_time)
            ret = func(self, *args, **kwargs)
            log.warning('线程:%s, 父进程:%s, 耗时:%s, <Task (%s) finished!!!>' % (
                threading.current_thread().getName(), os.getpid(), time.time() - start_time, func.__name__))
            return ret
        return inner
    return wrapper


def Executor():
    '''执行shell命令的类方法装饰器:
        - 用于类方法 可接收参数self
        - 对比v1版本的Executor 将添加命令前缀order_prefix的工作在装饰器内做了统一处理
    '''
    def wrapper(method):
        @functools.wraps(method)
        def inner(self, *args, **kwargs):
            res = method(self, *args, **kwargs)
            order = copy.deepcopy(self.order_prefix)
            order.extend(res)
            # order.extend([self.get_output_path(suffix=method.__name__)])

            print('order', order)
            p = subprocess.Popen(order, stdout=subprocess.PIPE)
            log.debug('Executor waiting...', order)
            result = {
                'returncode': p.wait(),
                'result': p.communicate()[0],
            }
            log.debug('Executor finish!', result)
            return dict(res, **result) if type(res) == dict else result
        return inner
    return wrapper


def executor(func):
    '''执行shell命令的函数装饰器

    Arguments:
        func {[function]} -- [返回终端命令list的函数]

    Returns:
        [type] -- [description]
    '''
    @functools.wraps(func)
    def inner(*args, **kwargs):
        order = func(*args, **kwargs)
        p = subprocess.Popen(order, shell=False, stdout=subprocess.PIPE)
        # log.warning('Executor waiting...', order)
        result = {
            'returncode': p.wait(),
            'result': p.communicate()[0],
        }
        # log.debug('Executor finish!', order, result)
        return dict(order, **result) if type(order) == dict else result
    return inner
