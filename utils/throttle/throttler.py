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

__all__ = ['ProcessThrottler']

DEFAULT_SAMPLE_INTERVAL = 0.2
WINDOW_SIZE = 5
ZOMBIE_CHECK_INTERVAL = 25  # ~5 seconds at 0.2s per iteration
MIN_STOP_TIME = 0.5  # minimum seconds to keep process stopped
MAX_STOP_TIME = 30.0  # maximum seconds to keep process stopped


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
        self._cycles = 0
        self._stop_until = 0.0
        self._stop_started_at = 0.0

    @property
    def target(self) -> int:
        """Current CPU target percentage."""
        if self._override_target is not None:
            return self._override_target
        return self._target_fn()

    @target.setter
    def target(self, value: int):
        old = self._override_target
        self._override_target = value
        if self._is_stopped_state and old is not None and value != old:
            self._recalculate_stop(value)

    def stop(self):
        """Signal the throttler to stop its sampling loop."""
        self._stopped.set()

    def _sample_cpu(self) -> float:
        """Sample current CPU usage percentage for the tracked process.

        If sampling fails (transient error), returns 0.0 and continues.
        Genuine process death is detected by periodic os.kill(pid, 0)
        checks in _loop_once(), not by single-sample failures.
        """
        try:
            t1 = sample_cpu_time(self.pid)
            time.sleep(self.sample_interval)
            t2 = sample_cpu_time(self.pid)
        except (ProcessLookupError, OSError):
            logger.debug('PID %d sample failed, continuing', self.pid)
            return 0.0

        elapsed = t2 - t1
        if elapsed <= 0:
            return 0.0

        return (elapsed / self.sample_interval) * 100.0

    def _check_stopped(self) -> bool:
        """Check if process is currently stopped (SIGSTOP'd)."""
        return self._is_stopped_state

    def _recalculate_stop(self, new_target: int):
        """Recalculate stop duration when target changes mid-stop.

        Uses the last sample window average to compute a new stop_time.
        If the new target is at or above the average, wakes the process
        immediately. Otherwise adjusts _stop_until proportionally based
        on elapsed stop time.
        """
        if not self._samples or len(self._samples) < WINDOW_SIZE:
            return

        avg = sum(self._samples) / len(self._samples)
        now = time.time()

        if avg <= new_target:
            self._stop_until = 0.0
            logger.info(
                'PID %d target raised to %d%% >= avg %.1f%% — waking immediately',
                self.pid,
                new_target,
                avg,
            )
            return

        overshoot = avg / new_target
        new_stop_time = (self.sample_interval * WINDOW_SIZE) * (overshoot - 1)
        new_stop_time = max(MIN_STOP_TIME, min(MAX_STOP_TIME, new_stop_time))

        elapsed_stopped = now - self._stop_started_at
        remaining = max(MIN_STOP_TIME, new_stop_time - elapsed_stopped)
        self._stop_until = now + remaining

        logger.info(
            'PID %d target changed to %d%% mid-stop: '
            'avg=%.1f%% stop_time=%.1fs elapsed=%.1fs remaining=%.1fs',
            self.pid,
            new_target,
            avg,
            new_stop_time,
            elapsed_stopped,
            remaining,
        )

    def _loop_once(self):
        """Single iteration of the throttler control loop."""
        self._cycles += 1
        if self._cycles % ZOMBIE_CHECK_INTERVAL == 0:
            try:
                os.kill(self.pid, 0)
            except ProcessLookupError:
                self.zombie = True
                logger.info('PID %d no longer exists, marking zombie', self.pid)
                return

        current_target = self.target
        if current_target <= 0:
            return

        now = time.time()

        # Check if process should be resumed
        if self._check_stopped():
            if now >= self._stop_until:
                logger.info('PID %d stop time elapsed, sending SIGCONT', self.pid)
                try:
                    os.kill(self.pid, signal.SIGCONT)
                    self._is_stopped_state = False
                    self._samples.clear()
                except ProcessLookupError:
                    self.zombie = True
                except PermissionError:
                    logger.warning('No permission to SIGCONT PID %d', self.pid)
            else:
                time.sleep(self.sample_interval)
            return

        # Process is running — sample CPU
        cpu = self._sample_cpu()
        self._samples.append(cpu)

        if len(self._samples) < WINDOW_SIZE:
            return

        avg = sum(self._samples) / len(self._samples)

        if avg > current_target:
            overshoot = avg / current_target
            stop_time = (self.sample_interval * WINDOW_SIZE) * (overshoot - 1)
            stop_time = max(MIN_STOP_TIME, min(MAX_STOP_TIME, stop_time))
            self._stop_until = now + stop_time

            logger.info(
                'PID %d avg=%.1f%% > target=%d%%, stopping for %.1fs',
                self.pid,
                avg,
                current_target,
                stop_time,
            )
            try:
                os.kill(self.pid, signal.SIGSTOP)
                self._is_stopped_state = True
                self._stop_started_at = now
            except ProcessLookupError:
                self.zombie = True
            except PermissionError:
                logger.warning('No permission to SIGSTOP PID %d', self.pid)

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
