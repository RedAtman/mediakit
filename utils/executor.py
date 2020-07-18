import sys,os,time
from concurrent import futures
import threading, multiprocessing
from utils import log

def func(future):
    time.sleep(1)
    print('--------------func',id(future),future.result())
def func2(future):
    print('--------------func2',id(future),future.result())


class BoundedExecutor:
    """BoundedExecutor behaves as a ThreadPoolExecutor which will block on
    calls to submit() once the limit given as "bound" work items are queued for
    execution.
    :param bound: Integer - the maximum number of items in the work queue
    :param max_workers: Integer - the size of the thread pool
    """
    def __init__(self, bound, max_workers):
        self.executor = futures.ThreadPoolExecutor(max_workers=max_workers)
        self.semaphore = threading.Semaphore(bound + max_workers)
        self.lock = threading.Lock()

    """See concurrent.futures.Executor#submit"""
    def submit(self, fn, callback_list=[], *args, **kwargs):
        self.semaphore.acquire()
        try:
            future = self.executor.submit(fn, *args, **kwargs)
            # log.info('<submit> 任务:%s, 线程:%s(%s), 父进程:%s' % (sys._getframe().f_code.co_name,threading.current_thread().name,threading.current_thread().ident, os.getpid()))
        except:
            self.semaphore.release()
            raise
        else:
            future.add_done_callback(lambda x: self.semaphore.release())
            for callback in callback_list:
                future.add_done_callback(callback)
            # future.add_done_callback(func)
            # future.add_done_callback(func2)
            return future

    """See concurrent.futures.Executor#shutdown"""
    def shutdown(self, wait=True):
        # log.info('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe().f_code.co_name,threading.current_thread().getName(), os.getpid()))
        self.executor.shutdown(wait)