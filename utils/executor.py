from concurrent.futures import FIRST_COMPLETED, FIRST_EXCEPTION, Future, ThreadPoolExecutor, wait
import logging
import os
import threading
from typing import Any, Callable, Iterator, NamedTuple

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
        # os.cpu_count() 而不是 multiprocessing.cpu_count(): 后者为了一个数字把整个
        # multiprocessing 运行时拖进包, PyInstaller 的 onefile 子进程会因缺 array 而崩
        cpu_count = os.cpu_count() or 1
        max_workers = max_workers if max_workers <= cpu_count else cpu_count
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

    def results(self) -> Iterator[Any]:
        """Yield results in completion order, releasing each future as it is consumed.

        按完成顺序而不是按提交顺序: 消费完的 Future 立刻从 futures/mapper_future_args 里摘掉,
        峰值驻留从"整批 Future + 整批参数 + 整批结果"降到"结果 + 在飞的 Future".
        """
        pending = set(self.futures)
        while pending:
            done, pending = wait(pending, timeout=1, return_when=FIRST_COMPLETED)
            for future in done:
                if future in self.futures:
                    self.futures.remove(future)
                self.mapper_future_args.pop(future, None)
                yield future.result()

    def shutdown(self):
        """Release the semaphore on interrupt cleanup."""
        self.semaphore.release()

    def submit_all(self, tasks: list[Callable[[], str]], *args: Any, **kwargs: Any) -> None:
        # 不是生成器: 之前带 yield, 不迭代就一个任务都不会提交 (调用方只能靠 list() 触发),
        # 而那个 yield 出去的错误结果从来没被消费过.
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
