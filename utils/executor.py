from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os
import sys
import threading

from logger import logger

__all__ = [
    'BoundedExecutor',
    'TaskManager',
]


class BoundedExecutor:
    """BoundedExecutor behaves as a ThreadPoolExecutor which will block on
    calls to submit() once the limit given as "bound" work items are queued for
    execution.
    :param bound: Integer - the maximum number of items in the work queue
    :param max_workers: Integer - the size of the thread pool
    """

    def __init__(self, bound=0, max_workers=multiprocessing.cpu_count()):
        '''
        Arguments:
            bound {[type]} -- [description] (default: {0})

        Keyword Arguments:
            max_workers {[int]} -- [进程池worker数量 若未指定 则使用cpu个数作为默认值] (default: {multiprocessing.cpu_count()})
        '''
        # self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        # self.semaphore = threading.Semaphore(bound + max_workers)
        # self.lock = threading.Lock()

        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.semaphore = multiprocessing.Semaphore(bound + max_workers)
        self.lock = multiprocessing.Manager().Lock()

    # See concurrent.futures.Executor#submit
    def submit(self, fn, *args, callback_list: list=None, **kwargs):
        """Start a new task, blocks if queue is full."""
        callback_list = callback_list or []
        self.semaphore.acquire()
        try:
            future = self.executor.submit(fn, *args, **kwargs)
            # logger.warning(
            #     'Process: %s, Thread: %s, <Caller (%s) start...>, file: %s:%s %s',
            #     os.getpid(),
            #     threading.current_thread().name,
            #     # inspect.currentframe().f_code.co_name,
            #     sys._getframe().f_back.f_code.co_name,
            #     sys._getframe().f_back.f_code.co_filename,
            #     sys._getframe().f_back.f_code.co_firstlineno,
            #     ' '.join(command),
            # )
        except Exception as err:
            logger.exception(err)
            self.semaphore.release()
            raise err
        future.add_done_callback(lambda x: self.semaphore.release())
        for callback in callback_list:
            future.add_done_callback(callback)
        return future

    # See concurrent.futures.Executor#shutdown
    def shutdown(self, wait=True):
        self.executor.shutdown(wait)
        logger.info(
            '<All done!!!> Task: %s, Thread: %s, Parent Process: %s',
            sys._getframe().f_code.co_name,   # pylint: disable=protected-access
            threading.current_thread().name,
            os.getpid()
        )


class TaskManager:
    def __init__(self, max_workers=2):
        max_workers = max_workers if max_workers <= multiprocessing.cpu_count() else multiprocessing.cpu_count()
        logger.debug('TaskManager init, max_workers: %s', max_workers)
        # self.semaphore = multiprocessing.Semaphore(max_workers)
        self.semaphore = threading.Semaphore(max_workers)
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.futures = []
        # from multiprocessing import Manager
        # self.futures = Manager.list([])

    def submit(self, fn, *args, callback_list: list = None, **kwargs):
        """Start a new task, blocks if queue is full."""
        callback_list = callback_list or []
        with self.semaphore:
            _future = self.executor.submit(fn, *args, **kwargs)
            self.futures.append(_future)
            for _callback in callback_list:
                _future.add_done_callback(_callback)
            _future.add_done_callback(self._task_done)

    def _task_done(self, _future):
        """Called once task is done, releases the queue if blocked."""
        self.shutdown(False)
        return _future.result()

    def shutdown(self, wait=True):
        self.semaphore.release()
        # self.executor.shutdown(wait)
        # logger.info(
        #     '<All done!!!> Task: %s, Thread: %s, Parent Process: %s',
        #     sys._getframe().f_code.co_name,
        #     threading.current_thread().name,
        #     os.getpid()
        # )
