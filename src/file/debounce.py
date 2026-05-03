import threading
import logging
from typing import Callable


logger = logging.getLogger()


class DebounceBuffer:
    def __init__(
        self,
        callback: Callable[[list[str]], None],
        calm_period: float = 5.0,
        max_flush_interval: float = 60.0,
    ):
        self.buffer: set[str] = set()
        self.callback = callback
        self.calm_period = calm_period
        self.max_flush_interval = max_flush_interval
        self._timer: threading.Timer | None = None
        self._max_timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._stopped = False

    def add(self, path: str):
        with self._lock:
            if self._stopped:
                return
            self.buffer.add(path)
            self._reset_timer()
            if self._max_timer is None:
                self._max_timer = threading.Timer(
                    self.max_flush_interval, self._flush
                )
                self._max_timer.daemon = True
                self._max_timer.start()

    def _reset_timer(self):
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self.calm_period, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _flush(self):
        with self._lock:
            if self._max_timer is not None:
                self._max_timer.cancel()
                self._max_timer = None
            if not self.buffer:
                return
            paths = list(self.buffer)
            self.buffer.clear()
        try:
            self.callback(paths)
        except Exception:
            logger.exception('DebounceBuffer callback failed')

    def stop(self):
        with self._lock:
            self._stopped = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if self._max_timer is not None:
                self._max_timer.cancel()
                self._max_timer = None
