"""Central coordinator for dynamic CPU throttling."""

import glob
import logging
import os
import signal
import threading
import time
from typing import Optional

from .sampling import system_cpu_load
from .throttler import ProcessThrottler

logger = logging.getLogger()

__all__ = [
    'CPULimiterCoordinator',
]

LOAD_HIGH = 80.0
LOAD_MODERATE = 50.0
BUDGET_HIGH = 0.25
BUDGET_MODERATE = 0.50
BUDGET_FULL = 1.0
MIN_PER_WORKER = 25
PROFILES = [None, 100, 50, 25]
FILE_SCAN_INTERVAL = 2.0
FILE_OVERRIDE_PATTERN = '/tmp/media_handler_cpu_*'


class CPULimiterCoordinator:
    """Central coordinator for CPU throttling.

    Manages per-process throttlers, distributes CPU budget across
    workers, and handles manual overrides via SIGUSR1 and files.
    """

    def __init__(
        self,
        default_limit: int = 100,
        auto_mode: bool = True,
    ):
        self.default_limit = default_limit
        self.auto_mode = auto_mode
        self._lock = threading.RLock()
        self._throttlers: dict[int, dict] = {}
        self._manual_override_active = False
        self._manual_target: Optional[int] = None
        self._profile_index = 0
        self._monitor_stop = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True,
        )
        self._monitor_thread.start()
        self._setup_signal_handler()

    def _stop_monitor(self):
        """Stop the background monitor thread."""
        self._monitor_stop.set()

    def _setup_signal_handler(self):
        """Register SIGUSR1 handler for profile cycling."""
        try:
            signal.signal(signal.SIGUSR1, self._handle_sigusr1)
            logger.info('Registered SIGUSR1 handler for CPU profile cycling')
        except (ValueError, AttributeError) as err:
            logger.warning('Cannot register SIGUSR1 handler: %s', err)

    def _handle_sigusr1(self, signum, frame):
        """Handle SIGUSR1: cycle to next CPU profile."""
        logger.info('Received SIGUSR1, cycling CPU profile')
        self._next_profile()

    def _next_profile(self):
        """Cycle to the next CPU profile."""
        with self._lock:
            self._profile_index = (self._profile_index + 1) % len(PROFILES)
            profile_value = PROFILES[self._profile_index]

            if profile_value is None:
                self._manual_override_active = False
                self._manual_target = None
                logger.info('CPU profile: unlimited (auto mode)')
            else:
                self._manual_override_active = True
                self._manual_target = profile_value
                logger.info('CPU profile: %d%%', profile_value)

            self._apply_target_to_all()

    def _apply_target_to_all(self):
        """Push current target to all active throttlers."""
        with self._lock:
            if not self._throttlers:
                return
            per_worker = self._calculate_per_process_target()
            for pid, info in self._throttlers.items():
                info['throttler'].target = per_worker

    def attach(self, pid: int):
        """Register a new process for throttling."""
        with self._lock:
            if pid in self._throttlers:
                logger.debug('PID %d already attached', pid)
                return

            def target_fn():
                return self._calculate_per_process_target()

            throttler = ProcessThrottler(pid=pid, target_fn=target_fn)
            self._throttlers[pid] = {
                'throttler': throttler,
                'started_at': time.time(),
            }
            throttler.start()
            logger.info('Attached throttler for PID %d', pid)

    def detach(self, pid: int):
        """Unregister a process and stop its throttler."""
        with self._lock:
            info = self._throttlers.pop(pid, None)
        if info:
            info['throttler'].stop()
            logger.info('Detached throttler for PID %d', pid)

    def set_manual_override(self, target: int):
        """Set a manual CPU budget (total, distributed across workers)."""
        with self._lock:
            self._manual_override_active = True
            self._manual_target = target
            self._profile_index = 0
            logger.info('Manual override set: total budget = %d%%', target)
            self._apply_target_to_all()

    def clear_manual_override(self):
        """Clear manual override and return to auto mode."""
        with self._lock:
            self._manual_override_active = False
            self._manual_target = None
            self._profile_index = 0
            logger.info('Manual override cleared, returning to auto mode')
            self._apply_target_to_all()

    def _calculate_per_process_target(self) -> int:
        """Calculate target CPU percentage for each worker."""
        with self._lock:
            active_count = max(len(self._throttlers), 1)

            if self._manual_override_active and self._manual_target is not None:
                total_budget = float(self._manual_target)
            elif self.auto_mode:
                load = self._get_system_load_ratio()
                core_count = os.cpu_count() or 1
                if load > LOAD_HIGH:
                    total_budget = core_count * 100 * BUDGET_HIGH
                elif load > LOAD_MODERATE:
                    total_budget = core_count * 100 * BUDGET_MODERATE
                else:
                    total_budget = (
                        core_count * 100 * BUDGET_FULL
                        * (self.default_limit / 100.0)
                    )
            else:
                core_count = os.cpu_count() or 1
                total_budget = core_count * 100 * (self.default_limit / 100.0)

            per_worker = int(total_budget / active_count)
            return max(per_worker, MIN_PER_WORKER)

    def _get_system_load_ratio(self) -> float:
        """Get current system load as a percentage (0-100+)."""
        try:
            return system_cpu_load()
        except (NotImplementedError, OSError) as err:
            logger.debug('system_cpu_load failed: %s', err)
            return 0.0

    def _scan_file_override(self):
        """Check for file-based override commands."""
        files = glob.glob(FILE_OVERRIDE_PATTERN)
        if not files:
            return

        for filepath in sorted(files):
            try:
                basename = os.path.basename(filepath)
                parts = basename.rsplit('_', 1)
                if len(parts) == 2 and parts[1].isdigit():
                    target = int(parts[1])
                    logger.info(
                        'File override detected: %s → %d%%', basename, target,
                    )
                    self.set_manual_override(target)
                    os.remove(filepath)
                    return
            except (OSError, ValueError) as err:
                logger.warning(
                    'Failed to process override file %s: %s', filepath, err,
                )

    def _cleanup_zombies(self):
        """Remove zombie throttlers."""
        with self._lock:
            zombies = [
                pid for pid, info in self._throttlers.items()
                if info['throttler'].zombie
            ]
            for pid in zombies:
                info = self._throttlers.pop(pid)
                info['throttler'].stop()
                logger.info('Cleaned up zombie throttler for PID %d', pid)

    def _monitor_loop(self):
        """Background monitor loop: load, file overrides, cleanup."""
        logger.info('CPULimiterCoordinator monitor started')
        while not self._monitor_stop.is_set():
            try:
                self._scan_file_override()
                self._cleanup_zombies()
                if self.auto_mode and not self._manual_override_active:
                    self._apply_target_to_all()
                time.sleep(FILE_SCAN_INTERVAL)
            except Exception:
                logger.exception('CPULimiterCoordinator monitor error')
        logger.info('CPULimiterCoordinator monitor stopped')

    def shutdown(self):
        """Stop the coordinator and all throttlers."""
        logger.info('Shutting down CPULimiterCoordinator')
        self._monitor_stop.set()
        with self._lock:
            for pid, info in list(self._throttlers.items()):
                info['throttler'].stop()
            self._throttlers.clear()
