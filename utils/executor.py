from concurrent.futures import FIRST_EXCEPTION, Future, ThreadPoolExecutor, wait
import logging
import multiprocessing
import threading
from typing import Any, Callable, NamedTuple

from utils.response import Result

logger = logging.getLogger()

__all__ = ['TaskManager']


class _FutureContext(NamedTuple):
    future: Future[Any]
    fn: Callable[..., Any]
    args: Any
    kwargs: Any


class TaskManager:
    PoolExecutor = ThreadPoolExecutor

    # PoolExecutor = ProcessPoolExecutor
    def __init__(self, max_workers: int = 1):
        max_workers = max_workers if max_workers <= multiprocessing.cpu_count() else multiprocessing.cpu_count()
        # self.semaphore = multiprocessing.Semaphore(max_workers)
        self.semaphore = threading.Semaphore(max_workers)
        self.executor = self.PoolExecutor(max_workers=max_workers)
        self.futures: list[Future[str]] = []
        self.mapper_future_args: dict[Future[Any], _FutureContext] = {}
        # from multiprocessing import Manager
        # self.futures = Manager.list([])

    def submit(self, fn: Callable[..., Any], *args: Any, callback_list: list[Callable[..., Any]] = [], **kwargs: Any):
        """Start a new task, blocks if queue is full."""
        with self.semaphore:
            _future: Future[Any] = self.executor.submit(fn, *args, **kwargs)
            self.futures.append(_future)
            self.mapper_future_args[_future] = _FutureContext(_future, fn, args, kwargs)
            for _callback in callback_list:
                _future.add_done_callback(_callback)

    def shutdown(self):
        """Release the semaphore on interrupt cleanup."""
        self.semaphore.release()

    def submit_all(self, tasks: list[Callable[[], str]], *args: Any, **kwargs: Any):
        with self.executor:
            _ = [self.submit(task, *args, **kwargs) for task in tasks]

            not_done = self.futures
            try:
                while not_done:
                    done, not_done = wait(not_done, timeout=1, return_when=FIRST_EXCEPTION)

            # Cancel any futures not done on KeyboardInterrupt
            except KeyboardInterrupt as err:
                logger.exception(err)
                for future in self.futures:
                    if not future.done():
                        future_context = self.mapper_future_args[future]
                        future.cancel()
                        result = Result(
                            601,
                            msg=err,
                            data={
                                # TODO: Not recommended to use fn.args[0] to obtain the handler
                                'media': future_context.fn.args[0]
                            },
                        )
                        future.set_result(result)
                self.shutdown()
                raise
            except Exception as err:
                logger.exception(err)
                yield Result(1, err)
