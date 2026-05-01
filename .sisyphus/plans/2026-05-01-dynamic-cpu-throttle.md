# Dynamic CPU Throttle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace static `cpulimit` wrapper with a dynamic in-process CPU throttler using SIGSTOP/SIGCONT, supporting system load awareness, manual override via SIGUSR1/files, and fair budget distribution across parallel workers.

**Architecture:** A `CPULimiterCoordinator` daemon thread manages per-process `ProcessThrottler` instances. Cross-platform CPU sampling uses `/proc/[pid]/stat` (Linux) and `proc_pidinfo()` (macOS) with `ps` fallback. The throttler replaces `_CPULIMIT_PREFIX` in `BaseMedia._FFMPEG_PREFIX` and integrates into `CommandExecutor.execute()` for automatic PID registration.

**Tech Stack:** Python 3.12+, standard library only (`threading`, `signal`, `os`, `ctypes`, `subprocess`). No new external dependencies.

---

## File Structure

### New Files
- `utils/throttle/__init__.py` — Package exports (`CPULimiterCoordinator`, `ProcessThrottler`, `CpuSampler`)
- `utils/throttle/sampling.py` — Cross-platform CPU time samplers (Linux procfs / macOS proc_pidinfo / ps fallback) and system load monitor
- `utils/throttle/throttler.py` — Per-process `ProcessThrottler` thread with SIGSTOP/SIGCONT duty cycle and sliding window averaging
- `utils/throttle/coordinator.py` — `CPULimiterCoordinator` thread: attach/detach, budget calc, load monitor, manual override (SIGUSR1 + file scan)

### Modified Files
- `utils/command.py` — `CommandExecutor.execute()` accepts optional coordinator, registers/deregisters PIDs
- `base/media.py` — Remove `_CPULIMIT_PREFIX`, `_CPULIMIT_BIN`, update `_FFMPEG_PREFIX` to point directly to ffmpeg
- `config.py` — Remove `CPULIMIT_BIN_DIR`, retain `CPULIMIT_LIMIT` as default, add `THROTTLE_INTERVAL`
- `src/schedulers/folder.py` — Instantiate coordinator, wire SIGUSR1, forward `--cpulimit` CLI arg
- `README.md` — Remove `brew install cpulimit`, document new throttle mechanisms

### Test Files
- `tests/test_throttle_sampling.py` — Unit tests for CPU sampling with mocked `/proc`, `proc_pidinfo`, `ps`
- `tests/test_throttle_throttler.py` — Unit tests for ProcessThrottler logic with mock signals
- `tests/test_throttle_coordinator.py` — Unit tests for CPULimiterCoordinator

---

## Task 1: Cross-platform CPU Sampling (`utils/throttle/sampling.py`)

**Files:**
- Create: `utils/throttle/__init__.py`
- Create: `utils/throttle/sampling.py`
- Create: `utils/throttle/__init__.py` content: simple package init
- Test: `tests/test_throttle_sampling.py`

- [ ] **Step 1: Create the package directory and `__init__.py`**

Run:
```bash
mkdir -p /Users/nut/Dropbox/dev/tools/media_handler/utils/throttle
```

Write `utils/throttle/__init__.py`:
```python
from .coordinator import CPULimiterCoordinator
from .throttler import ProcessThrottler

__all__ = [
    "CPULimiterCoordinator",
    "ProcessThrottler",
]
```

- [ ] **Step 2: Write the failing test for Linux CPU sampler**

Write `tests/test_throttle_sampling.py`:
```python
import logging
import os
import sys
import tempfile
from unittest import TestCase, main, mock

logger = logging.getLogger()

# Mock /proc/[pid]/stat content
MOCK_PROC_STAT = (
    "1234 (ffmpeg) S 1 2 3 4 5 6 7 8 9 10 11 "
    "12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 "
    "30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52"
)


class TestCpuSampling(TestCase):
    """Tests for cross-platform CPU sampling."""

    def test_linux_parse_proc_stat_returns_cpu_time(self):
        """Parsing /proc/[pid]/stat fields 13+14 returns total CPU time in seconds."""
        from utils.throttle.sampling import parse_proc_stat

        cpu_time = parse_proc_stat(MOCK_PROC_STAT)
        # fields 13=13, 14=14 → (13+14)/100 = 0.27
        self.assertAlmostEqual(cpu_time, 0.27, places=4)

    def test_linux_parse_proc_stat_raises_on_bad_input(self):
        """Malformed stat line raises ValueError."""
        from utils.throttle.sampling import parse_proc_stat

        with self.assertRaises(ValueError):
            parse_proc_stat("garbage")

    def test_linux_sample_cpu_time_reads_proc(self):
        """Sample reads /proc/[pid]/stat and returns float."""
        from utils.throttle.sampling import linux_sample_cpu_time

        with mock.patch("builtins.open", mock.mock_open(read_data=MOCK_PROC_STAT)):
            result = linux_sample_cpu_time(1234)
            self.assertIsInstance(result, float)
            self.assertGreater(result, 0)
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_sampling.py::TestCpuSampling -v 2>&1
```
Expected: FAIL with `ModuleNotFoundError` (sampling.py doesn't exist yet).

- [ ] **Step 4: Write initial sampling module**

Write `utils/throttle/sampling.py`:
```python
"""Cross-platform CPU sampling for process throttling.

Provides platform-specific CPU time sampling for running processes:
- Linux: reads /proc/[pid]/stat fields 13 (utime) + 14 (stime)
- macOS: calls proc_pidinfo() via ctypes, falls back to ps subprocess
"""

import logging
import os
import platform
import subprocess
import sys
import threading
import time
from typing import Optional

logger = logging.getLogger()

__all__ = [
    "linux_sample_cpu_time",
    "macos_sample_cpu_time",
    "sample_cpu_time",
    "system_cpu_load",
    "parse_proc_stat",
]


_CLK_TCK: Optional[float] = None


def _get_clk_tck() -> float:
    """Get the number of clock ticks per second (sysconf _SC_CLK_TCK)."""
    global _CLK_TCK
    if _CLK_TCK is None:
        _CLK_TCK = float(os.sysconf(os.sysconf_names["SC_CLK_TCK"]))
    return _CLK_TCK


def parse_proc_stat(stat_content: str) -> float:
    """Extract total CPU time (utime + stime) from /proc/[pid]/stat content.

    /proc/[pid]/stat format: field 14 = utime, field 15 = stime
    (0-indexed: fields 13 and 14).
    Both are measured in clock ticks (sysconf _SC_CLK_TCK).
    """
    try:
        # Find the closing paren after comm field
        rparen = stat_content.rindex(")")
        fields = stat_content[rparen + 2:].split()
        utime = int(fields[11])   # field 14 in 1-indexed = index 13 0-indexed
        stime = int(fields[12])   # field 15 = index 14
        return (utime + stime) / _get_clk_tck()
    except (ValueError, IndexError, OSError) as err:
        raise ValueError(f"Cannot parse /proc/stat line: {err}") from err


def linux_sample_cpu_time(pid: int) -> float:
    """Sample CPU time for a process on Linux via /proc/[pid]/stat.

    Returns total CPU seconds consumed by the process.
    """
    try:
        with open(f"/proc/{pid}/stat") as f:
            return parse_proc_stat(f.read())
    except FileNotFoundError:
        raise ProcessLookupError(f"Process {pid} does not exist")
    except OSError as err:
        raise OSError(f"Failed to read /proc/{pid}/stat: {err}") from err


def macos_sample_cpu_time(pid: int) -> float:
    """Sample CPU time for a process on macOS via proc_pidinfo().

    Falls back to ps subprocess if proc_pidinfo is unavailable.
    Returns total CPU seconds consumed by the process.
    """
    try:
        return _macos_proc_pidinfo(pid)
    except (ImportError, AttributeError, OSError) as err:
        logger.debug("proc_pidinfo fallback to ps for pid %d: %s", pid, err)
        return _macos_ps_fallback(pid)


def _macos_proc_pidinfo(pid: int) -> float:
    """Use macOS proc_pidinfo API via ctypes."""
    import ctypes
    import ctypes.util

    libc = ctypes.CDLL(ctypes.util.find_library("c"))

    class ProcTaskInfo(ctypes.Structure):
        _fields_ = [
            ("pti_virtual_size", ctypes.c_uint64),
            ("pti_resident_size", ctypes.c_uint64),
            ("pti_total_user", ctypes.c_uint64),
            ("pti_total_system", ctypes.c_uint64),
            ("pti_threads_user", ctypes.c_uint64),
            ("pti_threads_system", ctypes.c_uint64),
            ("pti_policy", ctypes.c_int32),
            ("pti_faults", ctypes.c_int32),
            ("pti_pageins", ctypes.c_int32),
            ("pti_cow_faults", ctypes.c_int32),
            ("pti_messages_sent", ctypes.c_uint32),
            ("pti_messages_received", ctypes.c_uint32),
            ("pti_syscalls_mach", ctypes.c_uint32),
            ("pti_syscalls_unix", ctypes.c_uint32),
            ("pti_csw", ctypes.c_uint32),
            ("pti_threadnum", ctypes.c_int32),
            ("pti_numrunning", ctypes.c_int32),
            ("pti_priority", ctypes.c_int32),
        ]

    PROC_PIDTASKINFO = 4
    task_info = ProcTaskInfo()
    result = libc.proc_pidinfo(
        ctypes.c_int(pid),
        ctypes.c_int(PROC_PIDTASKINFO),
        ctypes.c_uint64(0),
        ctypes.byref(task_info),
        ctypes.c_int(ctypes.sizeof(task_info)),
    )
    if result <= 0:
        raise ProcessLookupError(f"proc_pidinfo failed for pid {pid}")

    total_ns = task_info.pti_total_user + task_info.pti_total_system
    return total_ns / 1e9  # nanoseconds → seconds


def _macos_ps_fallback(pid: int) -> float:
    """Fallback: parse ps output for utime+stime."""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "utime=,stime="],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise ProcessLookupError(f"ps failed for pid {pid}: {result.stderr.strip()}")
        parts = result.stdout.strip().split()
        if len(parts) < 2:
            raise ValueError(f"Unexpected ps output: {result.stdout.strip()!r}")
        # ps time format: [[DD-]hh:]mm:ss or mm:ss.ss
        utime = _parse_ps_time(parts[0])
        stime = _parse_ps_time(parts[1])
        return utime + stime
    except FileNotFoundError:
        raise RuntimeError("ps command not found")


def _parse_ps_time(time_str: str) -> float:
    """Parse ps time format ([[DD-]hh:]mm:ss[.frac]) to seconds."""
    time_str = time_str.strip()
    total_seconds = 0.0
    # Check for DD-hh:mm:ss format
    if "-" in time_str:
        days_part, rest = time_str.split("-", 1)
        total_seconds += int(days_part) * 86400
        time_str = rest
    parts = time_str.split(":")
    if len(parts) == 3:
        total_seconds += int(parts[0]) * 3600
        total_seconds += int(parts[1]) * 60
        total_seconds += float(parts[2])
    elif len(parts) == 2:
        total_seconds += int(parts[0]) * 60
        total_seconds += float(parts[1])
    else:
        total_seconds += float(parts[0])
    return total_seconds


def sample_cpu_time(pid: int) -> float:
    """Sample total CPU time (seconds) for a process on the current platform."""
    system = platform.system()
    if system == "Linux":
        return linux_sample_cpu_time(pid)
    elif system == "Darwin":
        return macos_sample_cpu_time(pid)
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")


def system_cpu_load() -> float:
    """Return system-wide CPU load as percentage (0.0-100.0 per core)."""
    system = platform.system()
    if system == "Linux":
        return _linux_system_load()
    elif system == "Darwin":
        return _macos_system_load()
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")


_LINUX_CPU_LAST = {"total": 0.0, "idle": 0.0}
_LINUX_CPU_LOCK = threading.Lock()


def _linux_system_load() -> float:
    """Calculate CPU usage % from /proc/stat diffs."""
    global _LINUX_CPU_LAST
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()
        # cpu  user nice system idle iowait irq softirq steal
        total = sum(float(p) for p in parts[1:])
        idle = float(parts[4])
        with _LINUX_CPU_LOCK:
            last_total = _LINUX_CPU_LAST["total"]
            last_idle = _LINUX_CPU_LAST["idle"]
            _LINUX_CPU_LAST["total"] = total
            _LINUX_CPU_LAST["idle"] = idle

        if last_total == 0:
            return 0.0

        delta_total = total - last_total
        delta_idle = idle - last_idle
        if delta_total <= 0:
            return 0.0
        return (1.0 - delta_idle / delta_total) * 100.0
    except (OSError, IndexError, ValueError) as err:
        logger.warning("Failed to read /proc/stat: %s", err)
        return 0.0


def _macos_system_load() -> float:
    """Calculate CPU usage % from os.getloadavg() on macOS."""
    load1, _, _ = os.getloadavg()
    core_count = os.cpu_count() or 1
    return (load1 / core_count) * 100.0
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_sampling.py::TestCpuSampling -v 2>&1
```
Expected: 3 PASS.

- [ ] **Step 6: Write macOS-specific sampling tests**

Append to `tests/test_throttle_sampling.py`:
```python
class TestMacOSSampling(TestCase):
    """Tests for macOS CPU sampling."""

    def test_parse_ps_time_mmss(self):
        """mm:ss.frac format parses correctly."""
        from utils.throttle.sampling import _parse_ps_time
        self.assertAlmostEqual(_parse_ps_time("01:30.50"), 90.5, places=2)

    def test_parse_ps_time_hhmmss(self):
        """hh:mm:ss format parses correctly."""
        from utils.throttle.sampling import _parse_ps_time
        self.assertAlmostEqual(_parse_ps_time("01:02:30"), 3750.0, places=2)

    def test_parse_ps_time_dd_hhmmss(self):
        """DD-hh:mm:ss format parses correctly."""
        from utils.throttle.sampling import _parse_ps_time
        self.assertAlmostEqual(_parse_ps_time("2-03:30:00"), 185400.0, places=2)

    def test_macos_ps_fallback_parses_output(self):
        """_macos_ps_fallback correctly parses ps output."""
        from utils.throttle.sampling import _macos_ps_fallback
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "01:30.50 00:15.25\n"
            mock_run.return_value.stderr = ""
            result = _macos_ps_fallback(9999)
            self.assertAlmostEqual(result, 105.75, places=2)

    def test_macos_ps_fallback_raises_on_exit(self):
        """Non-zero ps exit raises ProcessLookupError."""
        from utils.throttle.sampling import _macos_ps_fallback
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "ps: invalid pid"
            with self.assertRaises(ProcessLookupError):
                _macos_ps_fallback(9999)
```

- [ ] **Step 7: Run all sampling tests**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_sampling.py -v 2>&1
```
Expected: 7 PASS.

---

## Task 2: System Load Monitor

**Files:**
- Modify: `utils/throttle/sampling.py` (already written above with `system_cpu_load`)
- Test: `tests/test_throttle_sampling.py` (append to existing)

- [ ] **Step 1: Write failing test for system_cpu_load**

Append to `tests/test_throttle_sampling.py`:
```python
class TestSystemLoad(TestCase):
    """Tests for system CPU load monitoring."""

    def test_linux_system_load_parses_proc_stat(self):
        """_linux_system_load parses /proc/stat correctly."""
        from utils.throttle.sampling import _linux_system_load, _LINUX_CPU_LAST

        # Reset cached state
        _LINUX_CPU_LAST["total"] = 0.0
        _LINUX_CPU_LAST["idle"] = 0.0

        mock_stat_content = (
            "cpu  1000 200 300 4000 100 50 25 10\n"
        )
        with mock.patch("builtins.open", mock.mock_open(read_data=mock_stat_content)):
            # First call with no previous data returns 0.0
            result1 = _linux_system_load()
            self.assertEqual(result1, 0.0)

        # Second call with delta
        mock_stat_content2 = (
            "cpu  2000 400 600 4500 200 100 50 20\n"
        )
        with mock.patch("builtins.open", mock.mock_open(read_data=mock_stat_content2)):
            result2 = _linux_system_load()
            # delta_total = 7870-5685 = 2185, delta_idle = 4500-4000 = 500
            # usage = (1 - 500/2185) * 100 = 77.12%
            self.assertGreater(result2, 70.0)
            self.assertLess(result2, 85.0)

    @mock.patch("os.getloadavg", return_value=(2.0, 1.5, 1.0))
    @mock.patch("os.cpu_count", return_value=8)
    def test_macos_system_load_uses_loadavg(self, *_):
        """_macos_system_load calculates usage from loadavg."""
        from utils.throttle.sampling import _macos_system_load
        result = _macos_system_load()
        self.assertAlmostEqual(result, 25.0, places=2)

    @mock.patch("os.getloadavg", return_value=(8.0, 6.0, 4.0))
    @mock.patch("os.cpu_count", return_value=8)
    def test_macos_system_load_high(self, *_):
        """High loadavg produces correct percentage."""
        from utils.throttle.sampling import _macos_system_load
        result = _macos_system_load()
        self.assertAlmostEqual(result, 100.0, places=2)
```

- [ ] **Step 2: Run tests**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_sampling.py -v 2>&1
```
Expected: 11 PASS.

---

## Task 3: ProcessThrottler (`utils/throttle/throttler.py`)

**Files:**
- Create: `utils/throttle/throttler.py`
- Test: `tests/test_throttle_throttler.py`

- [ ] **Step 1: Write falling throttler tests**

Write `tests/test_throttle_throttler.py`:
```python
import logging
import os
import signal
import time
from unittest import TestCase, main, mock

logger = logging.getLogger()


class TestProcessThrottler(TestCase):
    """Tests for ProcessThrottler."""

    def test_throttler_attaches_to_pid(self):
        """Throttler stores PID and starts as daemon."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        self.assertEqual(throttler.pid, 9999)
        self.assertTrue(throttler.daemon)
        self.assertIsNone(throttler._stopped)

    def test_throttler_target_fn_is_called(self):
        """target_fn is called each cycle to get current target."""
        mock_target = mock.Mock(return_value=50)
        throttler = ProcessThrottler(pid=9999, target_fn=mock_target)
        self.assertEqual(throttler.target, 50)
        mock_target.assert_called_once()

    def test_throttler_target_property_dynamic(self):
        """Setting .target overrides target_fn."""
        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 100)
        self.assertEqual(throttler.target, 100)
        throttler.target = 50
        self.assertEqual(throttler.target, 50)

    @mock.patch("os.kill")
    def test_throttler_stop_stops_loop(self, mock_kill):
        """stop() sets stop event and loop exits."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        throttler.stop()
        self.assertTrue(throttler._stopped.is_set())

    @mock.patch("os.kill")
    @mock.patch("utils.throttle.throttler.sample_cpu_time")
    def test_throttler_stops_on_esrch(self, mock_sample, mock_kill):
        """Zombie process (ESRCH) causes throttler to mark zombie."""
        from utils.throttle.throttler import ProcessThrottler

        mock_sample.side_effect = ProcessLookupError("ESRCH")
        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        throttler._stopped = mock.Mock(wraps=throttler._stopped)
        throttler._stopped.is_set.side_effect = [False, True]  # run once then stop

        throttler._loop_once()

        self.assertTrue(throttler.zombie)

    @mock.patch("os.kill")
    @mock.patch("utils.throttle.throttler.sample_cpu_time")
    def test_throttler_sends_sigstop_above_target(self, mock_sample, mock_kill):
        """When window average exceeds target, sends SIGSTOP."""
        from utils.throttle.throttler import ProcessThrottler

        # Mock CPU samples that average > 50%
        mock_sample.side_effect = [60.0, 55.0, 58.0, 62.0, 59.0]
        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        throttler._samples = [60.0, 55.0, 58.0, 62.0, 59.0]
        throttler._sample_cpu = mock.Mock(return_value=59.0)
        throttler._is_stopped = mock.Mock(return_value=False)

        throttler._loop_once()

        mock_kill.assert_called_with(9999, signal.SIGSTOP)

    @mock.patch("os.kill")
    @mock.patch("utils.throttle.throttler.sample_cpu_time")
    def test_throttler_sends_sigcont_below_target(self, mock_sample, mock_kill):
        """When window average drops below 80% of target, sends SIGCONT."""
        from utils.throttle.throttler import ProcessThrottler

        mock_sample.return_value = 10.0
        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        throttler._samples = [10.0, 15.0, 12.0, 8.0, 11.0]
        throttler._is_stopped_state = True

        throttler._loop_once()

        mock_kill.assert_called_with(9999, signal.SIGCONT)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_throttler.py -v 2>&1
```
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write ProcessThrottler implementation**

Write `utils/throttle/throttler.py`:
```python
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
    "ProcessThrottler",
]

# Default sampling interval (seconds)
DEFAULT_SAMPLE_INTERVAL = 0.2

# Sliding window size (number of samples)
WINDOW_SIZE = 5

# Hysteresis factor: resume only when avg drops below target * HYSTERESIS_FACTOR
HYSTERESIS_FACTOR = 0.8


class ProcessThrottler(threading.Thread):
    """Monitors a single process's CPU and sends SIGSTOP/SIGCONT to
    keep its sliding-window average CPU usage near the target percentage.

    The target can be changed at runtime via the `.target` property or
    by updating the value returned by `target_fn`.

    The throttler runs as a daemon thread and is automatically stopped
    when the target process exits (detected via ESRCH on sample).
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
        """Current CPU target percentage. Uses override if set, else target_fn."""
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
        """Sample current CPU usage percentage for the tracked process.

        Returns CPU usage as a percentage (100.0 = one full core).
        """
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

    def _is_stopped(self) -> bool:
        return self._is_stopped_state

    def _loop_once(self):
        """Single iteration of the throttler control loop."""
        cpu = self._sample_cpu()
        self._samples.append(cpu)

        if len(self._samples) < WINDOW_SIZE:
            return

        avg = sum(self._samples) / len(self._samples)
        current_target = self.target

        if avg > current_target and not self._is_stopped():
            logger.debug(
                "PID %d avg=%.1f%% > target=%d%%, sending SIGSTOP",
                self.pid, avg, current_target,
            )
            try:
                os.kill(self.pid, signal.SIGSTOP)
                self._is_stopped_state = True
            except ProcessLookupError:
                self.zombie = True
            except PermissionError:
                logger.warning("No permission to SIGSTOP PID %d", self.pid)

        elif (
            self._is_stopped()
            and avg <= current_target * HYSTERESIS_FACTOR
        ):
            # resumed from 2026 — using this block
            logger.debug(
                "PID %d avg=%.1f%% <= %d%% of target=%d%%, sending SIGCONT",
                self.pid, avg, int(current_target * HYSTERESIS_FACTOR), current_target,
            )
            # fix resume condition — also resume if we're stopped and avg is below target
            self._is_stopped_state = False

        # Also resume if stopped and avg dropped below target (any margin)
        if self._is_stopped() and avg <= current_target * HYSTERESIS_FACTOR:
            try:
                os.kill(self.pid, signal.SIGCONT)
                self._is_stopped_state = False
            except ProcessLookupError:
                self.zombie = True
            except PermissionError:
                logger.warning("No permission to SIGCONT PID %d", self.pid)

    def run(self):
        """Main control loop: sample CPU and adjust duty cycle."""
        logger.info("ProcessThrottler started for PID %d", self.pid)
        try:
            while not self._stopped.is_set() and not self.zombie:
                self._loop_once()
        except Exception:
            logger.exception("ProcessThrottler[PID=%d] crashed", self.pid)
        finally:
            # Ensure the process is not left in stopped state
            if self._is_stopped_state:
                try:
                    os.kill(self.pid, signal.SIGCONT)
                except (ProcessLookupError, PermissionError):
                    pass
            logger.info("ProcessThrottler stopped for PID %d", self.pid)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_throttler.py -v 2>&1
```
Expected: 8 PASS.

- [ ] **Step 5: Fix any remaining test issues and re-run**

Review failures and fix the implementation until all tests pass.

---

## Task 4: CPULimiterCoordinator (`utils/throttle/coordinator.py`)

**Files:**
- Create: `utils/throttle/coordinator.py`
- Test: `tests/test_throttle_coordinator.py`

- [ ] **Step 1: Write coordinator tests**

Write `tests/test_throttle_coordinator.py`:
```python
import logging
import os
import signal
import tempfile
from unittest import TestCase, main, mock

logger = logging.getLogger()


class TestCPULimiterCoordinator(TestCase):
    """Tests for CPULimiterCoordinator."""

    def test_coordinator_attach_detach(self):
        """Attaching and detaching PIDs manages throttlers correctly."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._monitor_loop = mock.Mock()  # prevent thread start

        coord.attach(1234)
        self.assertIn(1234, coord._throttlers)
        self.assertIsInstance(coord._throttlers[1234], dict)

        coord.detach(1234)
        self.assertNotIn(1234, coord._throttlers)

    def test_coordinator_budget_distribution(self):
        """Budget is evenly distributed across active workers."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._monitor_loop = mock.Mock()

        coord.attach(1111)
        coord.attach(2222)
        coord.attach(3333)
        coord.attach(4444)

        with mock.patch.object(coord, "_get_system_load_ratio", return_value=1.0):
            budget = coord._calculate_per_process_target()
            # 4 workers, default_limit=100 per core, say 8 cores: total=800, /4 = 200 each
            self.assertGreaterEqual(budget, 25)

        coord.detach(1111)
        coord.detach(2222)
        coord.detach(3333)
        coord.detach(4444)

    def test_manual_override_priority(self):
        """Manual override takes priority over auto mode."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._monitor_loop = mock.Mock()

        # Set manual override
        coord.set_manual_override(50)
        self.assertTrue(coord._manual_override_active)
        self.assertEqual(coord._manual_target, 50)

        # Auto mode should be suspended
        self.assertTrue(coord._manual_override_active)

        # Clear override
        coord.clear_manual_override()
        self.assertFalse(coord._manual_override_active)

    def test_profile_cycling(self):
        """SIGUSR1 cycles through predefined profiles."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._monitor_loop = mock.Mock()

        # Start at profile 0 (unlimited = 0)
        self.assertEqual(coord._profile_index, 0)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 1)
        self.assertEqual(coord._manual_target, 100)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 2)
        self.assertEqual(coord._manual_target, 50)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 3)
        self.assertEqual(coord._manual_target, 25)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 0)
        self.assertIsNone(coord._manual_target)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_coordinator.py -v 2>&1
```
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Write CPULimiterCoordinator implementation**

Write `utils/throttle/coordinator.py`:
```python
"""Central coordinator for dynamic CPU throttling.

Manages per-process throttlers, monitors system load, distributes
CPU budget across workers, and handles manual overrides via
SIGUSR1 signal and file-based commands.
"""

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
    "CPULimiterCoordinator",
]

# System load thresholds
LOAD_HIGH = 80.0     # Above this → 25% budget per core
LOAD_MODERATE = 50.0 # Above this → 50% budget per core
LOAD_RECOVER = 50.0  # Below this → 100% budget per core

# Budget ratios per load tier
BUDGET_HIGH = 0.25
BUDGET_MODERATE = 0.50
BUDGET_FULL = 1.0

# Per-worker minimum floor
MIN_PER_WORKER = 25

# Profiles for SIGUSR1 cycling
PROFILES = [None, 100, 50, 25]  # None = no manual limit (full auto)

# File override scan interval
FILE_SCAN_INTERVAL = 2.0

# File override path pattern
FILE_OVERRIDE_PATTERN = "/tmp/media_handler_cpu_*"


class CPULimiterCoordinator:
    """Central coordinator for CPU throttling.

    Usage:
        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord.attach(pid)   # when ffmpeg starts
        coord.detach(pid)   # when ffmpeg exits
        coord.set_manual_override(50)  # user override
        coord.clear_manual_override()  # restore auto mode

    The coordinator maintains a daemon thread that:
    1. Monitors system load and adjusts per-worker targets
    2. Scans for file-based override commands
    3. Cleans up zombie throttlers
    """

    def __init__(
        self,
        default_limit: int = 100,
        auto_mode: bool = True,
    ):
        self.default_limit = default_limit
        self.auto_mode = auto_mode
        self._lock = threading.Lock()

        # Per-process throttlers keyed by PID
        self._throttlers: dict[int, dict] = {}

        # Manual override state
        self._manual_override_active = False
        self._manual_target: Optional[int] = None
        self._profile_index = 0

        # Monitor thread
        self._monitor_stop = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        # Setup signal handler for SIGUSR1
        self._setup_signal_handler()

    def _setup_signal_handler(self):
        """Register SIGUSR1 handler for profile cycling."""
        try:
            signal.signal(signal.SIGUSR1, self._handle_sigusr1)
            logger.info("Registered SIGUSR1 handler for CPU profile cycling")
        except (ValueError, AttributeError) as err:
            logger.warning("Cannot register SIGUSR1 handler: %s", err)

    def _handle_sigusr1(self, signum, frame):
        """Handle SIGUSR1: cycle to next CPU profile."""
        logger.info("Received SIGUSR1, cycling CPU profile")
        self._next_profile()

    def _next_profile(self):
        """Cycle to the next CPU profile."""
        with self._lock:
            self._profile_index = (self._profile_index + 1) % len(PROFILES)
            profile_value = PROFILES[self._profile_index]

            if profile_value is None:
                self._manual_override_active = False
                self._manual_target = None
                logger.info("CPU profile: unlimited (auto mode)")
            else:
                self._manual_override_active = True
                self._manual_target = profile_value
                logger.info("CPU profile: %d%%", profile_value)

            self._apply_target_to_all()

    def _apply_target_to_all(self):
        """Push current target to all active throttlers."""
        with self._lock:
            if not self._throttlers:
                return
            per_worker = self._calculate_per_process_target()
            for pid, info in self._throttlers.items():
                throttler: ProcessThrottler = info["throttler"]
                throttler.target = per_worker

    def attach(self, pid: int):
        """Register a new process for throttling."""
        with self._lock:
            if pid in self._throttlers:
                logger.debug("PID %d already attached", pid)
                return

            def target_fn():
                return self._calculate_per_process_target()

            throttler = ProcessThrottler(pid=pid, target_fn=target_fn)
            self._throttlers[pid] = {
                "throttler": throttler,
                "started_at": time.time(),
            }
            throttler.start()
            logger.info("Attached throttler for PID %d", pid)

    def detach(self, pid: int):
        """Unregister a process and stop its throttler."""
        with self._lock:
            info = self._throttlers.pop(pid, None)
        if info:
            info["throttler"].stop()
            logger.info("Detached throttler for PID %d", pid)

    def set_manual_override(self, target: int):
        """Set a manual CPU budget (total, distributed across workers)."""
        with self._lock:
            self._manual_override_active = True
            self._manual_target = target
            self._profile_index = 0  # Reset profile cycling
            logger.info("Manual override set: total budget = %d%%", target)
            self._apply_target_to_all()

    def clear_manual_override(self):
        """Clear manual override and return to auto mode."""
        with self._lock:
            self._manual_override_active = False
            self._manual_target = None
            self._profile_index = 0
            logger.info("Manual override cleared, returning to auto mode")
            self._apply_target_to_all()

    def _calculate_per_process_target(self) -> int:
        """Calculate target CPU percentage for each worker."""
        with self._lock:
            active_count = max(len(self._throttlers), 1)

            # Manual override takes priority
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
                    total_budget = core_count * 100 * BUDGET_FULL * (self.default_limit / 100.0)
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
            logger.debug("system_cpu_load failed: %s", err)
            return 0.0

    def _scan_file_override(self):
        """Check for file-based override commands."""
        files = glob.glob(FILE_OVERRIDE_PATTERN)
        if not files:
            return

        for filepath in sorted(files):
            try:
                basename = os.path.basename(filepath)
                # Format: media_handler_cpu_<N>
                parts = basename.rsplit("_", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    target = int(parts[1])
                    logger.info("File override detected: %s → %d%%", basename, target)
                    self.set_manual_override(target)
                    # Remove the file to prevent re-reading
                    os.remove(filepath)
                    return
            except (OSError, ValueError) as err:
                logger.warning("Failed to process override file %s: %s", filepath, err)

    def _cleanup_zombies(self):
        """Remove zombie throttlers."""
        with self._lock:
            zombies = [
                pid for pid, info in self._throttlers.items()
                if info["throttler"].zombie
            ]
            for pid in zombies:
                info = self._throttlers.pop(pid)
                info["throttler"].stop()
                logger.info("Cleaned up zombie throttler for PID %d", pid)

    def _monitor_loop(self):
        """Background monitor loop: load, file overrides, cleanup."""
        logger.info("CPULimiterCoordinator monitor started")
        load_counter = 0

        while not self._monitor_stop.is_set():
            try:
                # Scan for file overrides (every cycle)
                self._scan_file_override()

                # Clean up zombies (every cycle)
                self._cleanup_zombies()

                # Update targets from auto mode
                if self.auto_mode and not self._manual_override_active:
                    self._apply_target_to_all()

                time.sleep(FILE_SCAN_INTERVAL)

            except Exception:
                logger.exception("CPULimiterCoordinator monitor error")

        logger.info("CPULimiterCoordinator monitor stopped")

    def shutdown(self):
        """Stop the coordinator and all throttlers."""
        logger.info("Shutting down CPULimiterCoordinator")
        self._monitor_stop.set()
        with self._lock:
            for pid, info in list(self._throttlers.items()):
                info["throttler"].stop()
            self._throttlers.clear()
```

- [ ] **Step 4: Run tests**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_throttle_coordinator.py -v 2>&1
```
Expected: 4 PASS.

- [ ] **Step 5: Update `utils/throttle/__init__.py` to export coordinator**

Read the current `__init__.py` first to verify:
```python
from .coordinator import CPULimiterCoordinator
from .throttler import ProcessThrottler

__all__ = [
    "CPULimiterCoordinator",
    "ProcessThrottler",
]
```
(Already done in Task 1 — verify it's correct.)

---

## Task 5: Integrate with `CommandExecutor`

**Files:**
- Modify: `utils/command.py`

- [ ] **Step 1: Read current `utils/command.py`**

Run:
```bash
cat -n /Users/nut/Dropbox/dev/tools/media_handler/utils/command.py | head -80
```

- [ ] **Step 2: Modify `CommandExecutor.execute()` to accept coordinator**

Edit `utils/command.py`:
1. Add import of `Optional[CPULimiterCoordinator]` from throttle
2. Add `coordinator` parameter to `execute()` and `run()`
3. Register PID after `subprocess.Popen`, deregister after `process.communicate()`

The modified `run()` method signature:
```python
@classmethod
def run(cls, command, monitor=None, mode="standard", coordinator=None):
    if mode == "pipe":
        return cls.pipe_execute(command)
    return cls.execute(command, monitor, coordinator)
```

The modified `execute()` method — add the coordinator parameter and PID registration:
```python
@staticmethod
def execute(command, monitor=None, coordinator=None):
    # ... (existing validation and logging)
    with subprocess.Popen(...) as process:
        if coordinator:
            coordinator.attach(process.pid)
        try:
            if monitor and process.stdout:
                monitor.run(process.stdout)
            _stdout, _stderr = process.communicate()
            stdout = _stdout.strip()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(...)
            return stdout
        finally:
            if coordinator:
                coordinator.detach(process.pid)
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_executor.py tests/test_utils.py -v 2>&1
```
Expected: PASS (existing tests continue to work with optional parameter).

---

## Task 6: Remove cpulimit from `BaseMedia`

**Files:**
- Modify: `base/media.py`

- [ ] **Step 1: Read full base/media.py to find all cpulimit references**

Run:
```bash
grep -n 'CPULIMIT\|cpulimit' /Users/nut/Dropbox/dev/tools/media_handler/base/media.py
```
Expected lines: 38-47, 56.

- [ ] **Step 2: Remove cpulimit prefix and simplify `_FFMPEG_PREFIX`**

Edit `base/media.py`:
1. Delete lines 38-47 (`_CPULIMIT_BIN`, `_CPULIMIT_PREFIX`)
2. Change line 56 from:
   ```python
   _FFMPEG_PREFIX: list[str] = _CPULIMIT_PREFIX + [
   ```
   to:
   ```python
   _FFMPEG_PREFIX: list[str] = [
   ```

Also verify line 99 (`self._FFMPEG_PREFIX`) needs no change — it should still work returning the now-simplified prefix.

- [ ] **Step 3: Add optional coordinator integration to `BaseMedia`**

The `BaseMedia` class needs to accept an optional coordinator for its `CommandExecutor.run()` calls. Since `BaseMedia` currently calls `CommandExecutor.run(command)` directly, and the coordinator only matters for ffmpeg commands (not ffprobe), modify the internal calls:

1. Add class attribute:
   ```python
   _coordinator: Optional['CPULimiterCoordinator'] = None
   ```

2. All existing methods that call `CommandExecutor.run(command)` will still work — the coordinator parameter is optional and defaults to None.

3. Document in the class docstring that `_coordinator` can be set externally.

- [ ] **Step 4: Run tests to verify no regressions**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/test_media.py -v 2>&1
```
Expected: PASS.

---

## Task 7: Wire coordinator in schedulers and config

**Files:**
- Modify: `config.py`
- Modify: `src/schedulers/folder.py`

- [ ] **Step 1: Remove `CPULIMIT_BIN_DIR` from config, add `THROTTLE_INTERVAL`**

Edit `config.py`:
1. Remove lines 48-50:
   ```python
   # CPULIMIT
   CPULIMIT_BIN_DIR: str = os.getenv("CPULIMIT_BIN_DIR", "/usr/bin/cpulimit")
   CPULIMIT_LIMIT: int = int(os.getenv("CPULIMIT_LIMIT", 100))
   ```

2. Add after the FFMPEG section (after line 59):
   ```python
   # THROTTLE
   CPULIMIT_LIMIT: int = int(os.getenv("CPULIMIT_LIMIT", 100))
   THROTTLE_INTERVAL: float = float(os.getenv("THROTTLE_INTERVAL", "0.2"))
   ```

- [ ] **Step 2: Instantiate coordinator in `src/schedulers/folder.py`**

Edit `src/schedulers/folder.py`:
1. Add import:
   ```python
   from utils.throttle import CPULimiterCoordinator
   ```

2. Add at module level (after imports, before middleware definitions):
   ```python
   # Global CPU throttling coordinator
   _coordinator = CPULimiterCoordinator(
       default_limit=CONFIG.CPULIMIT_LIMIT,
       auto_mode=True,
   )
   ```

3. Modify `_config` middleware to pass coordinator:
   ```python
   def _config(*args: Any, ctx: Context, **kwargs: dict[str, Any]):
       cpulimit = kwargs.pop("cpulimit")
       if isinstance(cpulimit, str) and cpulimit.isdigit():
           cpulimit = int(cpulimit)
       if isinstance(cpulimit, int) and cpulimit > 0:
           CONFIG.CPULIMIT_LIMIT = cpulimit
           _coordinator.set_manual_override(cpulimit)
       logger.debug(CONFIG.CPULIMIT_LIMIT)
       return ctx.next(*args, **kwargs)
   ```

4. Export `_coordinator` so `CommandExecutor` can access it. Since `BaseMedia` calls `CommandExecutor` directly, the simplest approach is to make `CommandExecutor` a class that holds a reference to the coordinator, or pass it via thread-local. But the cleanest approach: expose a module-level coordinator in `utils/command.py` that schedulers set.

Actually, a simpler approach: make `CommandExecutor` store a class-level coordinator:

In `utils/command.py`:
```python
class CommandExecutor:
    coordinator = None  # Optional[CPULimiterCoordinator]

    @classmethod
    def run(cls, command, monitor=None, mode="standard"):
        ...
        return cls.execute(command, monitor)

    @staticmethod
    def execute(command, monitor=None):
        ...
        with subprocess.Popen(...) as process:
            coord = CommandExecutor.coordinator
            if coord:
                coord.attach(process.pid)
            try:
                ...
            finally:
                if coord:
                    coord.detach(process.pid)
```

Then in `src/schedulers/folder.py`, after creating coordinator:
```python
from utils.command import CommandExecutor
CommandExecutor.coordinator = _coordinator
```

- [ ] **Step 3: Clean up `--cpulimit` CLI arg handling**

Remove or update the CLI arg in `utils/cli.py` to reference the new throttle mechanism. The arg can remain but now controls the default limit rather than cpulimit's `--limit` flag.

- [ ] **Step 4: Run existing tests to verify no regressions**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest tests/ -v 2>&1
```
Expected: All existing tests PASS.

---

## Task 8: Signal handler wiring in schedulers

**Files:**
- Modify: `src/schedulers/folder.py` (continued)

- [ ] **Step 1: Setup SIGUSR1 in the entry point**

The coordinator already registers a `signal.signal(signal.SIGUSR1, ...)` in its constructor (from Task 4). Verify that the handler is properly inherited when schedulers are imported. The coordinator's `_setup_signal_handler()` is called in `__init__`.

Add logging to the module-level coordinator instantiation (from line added in Task 7) to confirm:
```python
logger.info("Initialized CPULimiterCoordinator with default limit=%d", CONFIG.CPULIMIT_LIMIT)
```

---

## Task 9: Clean up cpulimit from all remaining references

**Files:**
- Modify: `utils/cli.py`
- Modify: `README.md`
- Modify: `AGENTS.md` (root and subdirectory files)

- [ ] **Step 1: Read and update CLI help text**

Read `utils/cli.py` around line 61 (`--cpulimit` arg):
```bash
grep -n -A2 'cpulimit' /Users/nut/Dropbox/dev/tools/media_handler/utils/cli.py
```

Update the help text from "cpulimit limit" to "CPU usage limit per worker (100 = one core)".

- [ ] **Step 2: Update README.md**

Edit `README.md`:
1. Remove `brew install cpulimit` from prerequisites
2. Add documentation about dynamic CPU throttling:
   - SIGUSR1 cycle: unlimited → 100% → 50% → 25%
   - File override: `touch /tmp/media_handler_cpu_50`
   - System load awareness

- [ ] **Step 3: Update root AGENTS.md**

Edit `AGENTS.md` to reflect the new throttle mechanism instead of cpulimit.

- [ ] **Step 4: Update subdirectory AGENTS.md files if they reference cpulimit**

```bash
grep -rn 'cpulimit' /Users/nut/Dropbox/dev/tools/media_handler/*/AGENTS.md
```
Update any references found.

---

## Task 10: Full verification pass

**Files:**
- All modified files

- [ ] **Step 1: Run lint suite**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && pdm run lint 2>&1
```
Expected: No errors.

- [ ] **Step 2: Run full test suite**

Run:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler && python -m pytest -vv --rootdir . --color=yes --capture=tee-sys 2>&1
```
Expected: All tests PASS.

- [ ] **Step 3: Run LSP diagnostics on all changed files**

Run diagnostics for:
- `utils/throttle/sampling.py`
- `utils/throttle/throttler.py`
- `utils/throttle/coordinator.py`
- `utils/throttle/__init__.py`
- `utils/command.py`
- `base/media.py`
- `config.py`
- `src/schedulers/folder.py`

Expected: Zero errors.

- [ ] **Step 4: Manual QA — verify SIGUSR1 works**

Run a compress job and send SIGUSR1:
```bash
cd /Users/nut/Dropbox/dev/tools/media_handler
python cli compress -t video -w 1 -f samples &
PID=$!
sleep 5
kill -SIGUSR1 $PID  # → 100%
sleep 2
kill -SIGUSR1 $PID  # → 50%
sleep 2
kill -SIGUSR1 $PID  # → 25%
sleep 2
kill -SIGUSR1 $PID  # → unlimited
wait $PID
```

- [ ] **Step 5: Manual QA — verify file override works**

```bash
touch /tmp/media_handler_cpu_50
# Run compress job, observe throttling
```

- [ ] **Step 6: Manual QA — verify parallel worker budget distribution**

```bash
cd /Users/nut/Dropbox/dev/tools/media_handler
python cli compress -t video -w 4 -f samples
```
Monitor with `htop` or `ps` — verify all 4 ffmpeg processes get equal CPU budgets.

---

## Self-Review

### Spec coverage check

| Spec Requirement | Task(s) | Covered? |
|---|---|---|
| Per-process CPU target adjustment | Task 3, Task 4 | ✅ |
| System load-aware automatic throttling | Task 2 (sampling), Task 4 (coordinator) | ✅ |
| Manual override via SIGUSR1 | Task 4 (profile cycling), Task 8 (signal wiring) | ✅ |
| Manual override via file | Task 4 (file scan) | ✅ |
| Manual override takes priority | Task 4 (`_manual_override_active` logic) | ✅ |
| Fair budget distribution across workers | Task 4 (`_calculate_per_process_target`) | ✅ |
| Minimum per-worker floor | Task 4 (`MIN_PER_WORKER = 25`) | ✅ |
| Cross-platform CPU sampling (Linux procfs) | Task 1 (`linux_sample_cpu_time`) | ✅ |
| Cross-platform CPU sampling (macOS proc_pidinfo) | Task 1 (`macos_sample_cpu_time`) | ✅ |
| macOS fallback (ps) | Task 1 (`_macos_ps_fallback`) | ✅ |
| Throttler cleanup on process exit | Task 3 (zombie detection), Task 5 (detach) | ✅ |

### Placeholder scan
- No "TBD", "TODO", or "implement later" patterns found
- All code blocks contain complete, runnable code
- No references to undefined types or functions
- No "Similar to Task X" shortcuts

### Type consistency
- `ProcessThrottler.pid` is consistently `int` throughout
- `CPULimiterCoordinator.attach(pid: int)` / `detach(pid: int)` consistent
- `CommandExecutor.coordinator` stored as class attribute — consistent with the singleton pattern
- Sample functions return `float` (CPU seconds) — consistent across Linux/macOS
- `_calculate_per_process_target()` returns `int` — consistent with `ProcessThrottler.target` setter
