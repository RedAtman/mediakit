import os
import time
import logging
from typing import Protocol


logger = logging.getLogger()


class _SizeGetter(Protocol):
    def __call__(self, path: str) -> int: ...


class FileStabilityTracker:
    def __init__(
        self,
        stable_samples: int = 3,
        sample_interval: float = 1.0,
        timeout: float = 30.0,
        size_getter: _SizeGetter | None = None,
    ):
        self.stable_samples = stable_samples
        self.sample_interval = sample_interval
        self.timeout = timeout
        self._size_getter = size_getter
        self._state: dict[str, _PerPathState] = {}

    def wait_until_stable(self, path: str) -> bool:
        if path not in self._state:
            self._state[path] = _PerPathState(self.stable_samples)
        state = self._state[path]
        deadline = time.monotonic() + self.timeout
        getter = self._size_getter if self._size_getter is not None else os.path.getsize
        while time.monotonic() < deadline:
            try:
                current_size = getter(path)
            except FileNotFoundError:
                logger.warning('File vanished while checking stability: %s', path)
                return False
            if state.record_sample(current_size):
                del self._state[path]
                return True
            time.sleep(self.sample_interval)
        del self._state[path]
        return True


class _PerPathState:
    def __init__(self, required_stable: int):
        self._last_size: int | None = None
        self._stable_count = 0
        self._required_stable = required_stable

    def record_sample(self, size: int) -> bool:
        if size == self._last_size:
            self._stable_count += 1
        else:
            self._stable_count = 0
        self._last_size = size
        return self._stable_count >= self._required_stable
