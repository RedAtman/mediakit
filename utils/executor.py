from concurrent.futures import (
    ALL_COMPLETED,
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    wait,
)
import logging
import multiprocessing
import os
from queue import Queue
import sys
import threading
from types import FunctionType, MethodType
from typing import Any, Callable, List


logger = logging.getLogger()

__all__ = [
    "BoundedExecutor",
    "TaskManager",
]


class BoundedExecutor:
    """BoundedExecutor behaves as a ThreadPoolExecutor which will block on
    calls to submit() once the limit given as "bound" work items are queued for
    execution.
    :param bound: Integer - the maximum number of items in the work queue
    :param max_workers: Integer - the size of the thread pool
    """

    def __init__(self, bound=0, max_workers=multiprocessing.cpu_count()):
        """
        Arguments:
            bound {[type]} -- [description] (default: {0})

        Keyword Arguments:
            max_workers {[int]} -- [进程池worker数量 若未指定 则使用cpu个数作为默认值] (default: {multiprocessing.cpu_count()})
        """
        # self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        # self.semaphore = threading.Semaphore(bound + max_workers)
        # self.lock = threading.Lock()

        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.semaphore = multiprocessing.Semaphore(bound + max_workers)
        self.lock = multiprocessing.Manager().Lock()

    # See concurrent.futures.Executor#submit
    def submit(
        self, fn, *args, callback_list: List[FunctionType | MethodType] = [], **kwargs
    ):
        """Start a new task, blocks if queue is full."""
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
            "<All done!!!> Task: %s, Thread: %s, Parent Process: %s",
            sys._getframe().f_code.co_name,  # pylint: disable=protected-access
            threading.current_thread().name,
            os.getpid(),
        )


class TaskManager:
    PoolExecutor = ThreadPoolExecutor

    # PoolExecutor = ProcessPoolExecutor
    def __init__(self, max_workers: int = 1):
        max_workers = (
            max_workers
            if max_workers <= multiprocessing.cpu_count()
            else multiprocessing.cpu_count()
        )
        # self.semaphore = multiprocessing.Semaphore(max_workers)
        self.semaphore = threading.Semaphore(max_workers)
        self.executor = self.PoolExecutor(max_workers=max_workers)
        self.futures: List[Future[str]] = []
        self.queue: Queue[List[Any]] = Queue()
        # from multiprocessing import Manager
        # self.futures = Manager.list([])

    def submit_all(
        self,
        tasks: List[Callable[[], str]],
        is_wait: bool = True,
        *args: Any,
        **kwargs: Any
    ):
        with self.executor:
            futures = [self.submit(task, *args, **kwargs) for task in tasks]
            logger.info("All media have been processed.")
            if is_wait:
                wait(self.futures, return_when=ALL_COMPLETED)
                logger.info(("ALL_COMPLETED", self.futures))

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        callback_list: List[Callable[..., Any]] = [],
        **kwargs: Any
    ):
        """Start a new task, blocks if queue is full."""
        with self.semaphore:
            _future = self.executor.submit(fn, *args, **kwargs)
            self.futures.append(_future)
            for _callback in callback_list:
                _future.add_done_callback(_callback)
            _future.add_done_callback(self._task_done)

    def _task_done(self, _future: Future[Any]):
        """Called once task is done, releases the queue if blocked."""
        result = _future.result()
        logger.info("TaskManager._task_done: %s", result)
        self.queue.put(result)
        self.shutdown(False)
        return result

    def shutdown(self, wait=True):
        self.semaphore.release()
        # self.executor.shutdown(wait)
        # logger.info(
        #     '<All done!!!> Task: %s, Thread: %s, Parent Process: %s',
        #     sys._getframe().f_code.co_name,
        #     threading.current_thread().name,
        #     os.getpid()
        # )
