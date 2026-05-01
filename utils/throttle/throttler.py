"""Per-process CPU throttler using SIGSTOP/SIGCONT duty cycle."""

import logging
import os
import signal
import threading
import time
from collections import deque
from typing import Callable, Optional

from .sampling import sample_cpu_time

logger = logging.getLogger()

__all__ = [
    'ProcessThrottler',
]

DEFAULT_SAMPLE_INTERVAL = 0.2
WINDOW_SIZE = 5
HYSTERESIS_FACTOR = 0.8


class ProcessThrottler(threading.Thread):
    """Monitors a single process's CPU and sends SIGSTOP/SIGCONT to
    keep its sliding-window average CPU usage near the target percentage.

    The target can be changed at runtime via the target property or
    by updating the value returned by target_fn.

    Runs as a daemon thread. Automatically stops when the target
    process exits (detected via ESRCH on sample).
    """

    def __init__(
        self,
        pid: int,
        target_fn: Callable[[], int],
        sample_interval: float = DEFAULT_SAMPLE_INTERVAL,
    ):
        super().__init__(daemon=True)
        self.pid = pid
        self._target_fn = target_fn
        self._override_target: Optional[int] = None
        self.sample_interval = sample_interval
        self._samples: deque = deque(maxlen=WINDOW_SIZE)
        self._stopped = threading.Event()
        self._is_stopped_state = False
        self.zombie = False

    @property
    def target(self) -> int:
        """Current CPU target percentage."""
        if self._override_target is not None:
            return self._override_target
        return self._target_fn()

    @target.setter
    def target(self, value: int):
        self._override_target = value

    def stop(self):
        """Signal the throttler to stop its sampling loop."""
        self._stopped.set()

    def _sample_cpu(self) -> float:
        """Sample current CPU usage percentage for the tracked process."""
        try:
            t1 = sample_cpu_time(self.pid)
            time.sleep(self.sample_interval)
            t2 = sample_cpu_time(self.pid)
        except (ProcessLookupError, OSError):
            self.zombie = True
            return 0.0

        elapsed = t2 - t1
        if elapsed <= 0:
            return 0.0

        return (elapsed / self.sample_interval) * 100.0

    def _check_stopped(self) -> bool:
        """Check if process is currently stopped (SIGSTOP'd)."""
        return self._is_stopped_state

    def _loop_once(self):
        """Single iteration of the throttler control loop."""
        cpu = self._sample_cpu()
        self._samples.append(cpu)

        if len(self._samples) < WINDOW_SIZE:
            return

        avg = sum(self._samples) / len(self._samples)
        current_target = self.target

        if avg > current_target and not self._check_stopped():
            logger.debug(
                'PID %d avg=%.1f%% > target=%d%%, sending SIGSTOP',
                self.pid, avg, current_target,
            )
            try:
                os.kill(self.pid, signal.SIGSTOP)
                self._is_stopped_state = True
            except ProcessLookupError:
                self.zombie = True
            except PermissionError:
                logger.warning('No permission to SIGSTOP PID %d', self.pid)

        if self._check_stopped() and avg <= current_target * HYSTERESIS_FACTOR:
            logger.debug(
                'PID %d avg=%.1f%% <= %d%% of target=%d%%, sending SIGCONT',
                self.pid, avg, int(current_target * HYSTERESIS_FACTOR),
                current_target,
            )
            try:
                os.kill(self.pid, signal.SIGCONT)
                self._is_stopped_state = False
            except ProcessLookupError:
                self.zombie = True
            except PermissionError:
                logger.warning('No permission to SIGCONT PID %d', self.pid)

    def run(self):
        """Main control loop: sample CPU and adjust duty cycle."""
        logger.info('ProcessThrottler started for PID %d', self.pid)
        try:
            while not self._stopped.is_set() and not self.zombie:
                self._loop_once()
        except Exception:
            logger.exception('ProcessThrottler[PID=%d] crashed', self.pid)
        finally:
            if self._is_stopped_state:
                try:
                    os.kill(self.pid, signal.SIGCONT)
                except (ProcessLookupError, PermissionError):
                    pass
            logger.info('ProcessThrottler stopped for PID %d', self.pid)
