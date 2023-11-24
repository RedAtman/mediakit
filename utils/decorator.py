import functools
import time
import os
import threading
import subprocess
from logger import logger


def timer(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        logger.debug('Task start(%s): %s', func.__name__, start_time)
        result = func(self, *args, **kwargs)
        logger.debug(
            '线程:%s, 父进程:%s, <Task (%s) finished!!!>. 耗时:%s.',
            threading.current_thread().name,
            os.getpid(),
            func.__name__,
            time.time() - start_time,
        )
        return result

    return wrapper


def execute_shell_command(func):
    '''执行shell命令的类方法装饰器:
        - 用于类方法 可接收参数self
        - 将添加命令前缀order_prefix的工作在装饰器内做统一处理
        - 执行shell命令的函数装饰器
    '''
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):

        # Call the original function to get the shell command
        shell_command, new_file_path = func(self, *args, **kwargs)

        # Execute the shell command
        process = subprocess.Popen(
            shell_command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, shell_command, stderr.decode('utf-8'))
        # log.warning('Executor waiting...', order)
        # result = {
        #     'returncode': process.wait(),
        #     # 'result': process.communicate()[0],
        #     'result': stdout.decode('utf-8'),
        #     'file_path': new_file_path,
        # }
        # log.debug('Executor finish!', order, result)
        return result

    return wrapper


class classproperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)
