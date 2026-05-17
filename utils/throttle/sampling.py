"""Cross-platform CPU sampling for process throttling.

Provides platform-specific CPU time sampling for running processes:
- Linux: reads /proc/[pid]/stat fields 13 (utime) + 14 (stime)
- macOS: calls proc_pidinfo() via ctypes, falls back to ps subprocess
"""

import logging
import os
import platform
import subprocess
import threading
from typing import Optional

logger = logging.getLogger(__name__)

__all__ = [
    'linux_sample_cpu_time',
    'macos_sample_cpu_time',
    'sample_cpu_time',
    'system_cpu_load',
    'parse_proc_stat',
]

_CLK_TCK: Optional[float] = None


def _get_clk_tck() -> float:
    """Get clock ticks per second (sysconf _SC_CLK_TCK)."""
    global _CLK_TCK  # noqa: PLW0603
    if _CLK_TCK is None:
        _CLK_TCK = float(os.sysconf(os.sysconf_names['SC_CLK_TCK']))
    return _CLK_TCK


def parse_proc_stat(stat_content: str) -> float:
    """Extract total CPU time (utime + stime) from /proc/[pid]/stat.

    Format: fields 14 (utime) and 15 (stime), 0-indexed as 13 and 14.
    Both are in clock ticks; divide by sysconf _SC_CLK_TCK for seconds.
    """
    try:
        rparen = stat_content.rindex(')')
        fields = stat_content[rparen + 2:].split()
        utime = int(fields[11])
        stime = int(fields[12])
        return (utime + stime) / _get_clk_tck()
    except (ValueError, IndexError, OSError) as err:
        raise ValueError(f'Cannot parse /proc/stat line: {err}') from err


def linux_sample_cpu_time(pid: int) -> float:
    """Sample CPU time for a process on Linux via /proc/[pid]/stat.

    Returns total CPU seconds consumed by the process.
    """
    try:
        with open(f'/proc/{pid}/stat') as f:
            return parse_proc_stat(f.read())
    except FileNotFoundError as err:
        raise ProcessLookupError(f'Process {pid} does not exist') from err
    except OSError as err:
        raise OSError(f'Failed to read /proc/{pid}/stat: {err}') from err


def macos_sample_cpu_time(pid: int) -> float:
    """Sample CPU time for a process on macOS.

    Uses ps subprocess as the primary method since proc_pidinfo()
    returns incorrect CPU time values on macOS 26+ (struct layout
    mismatch). Falls back to proc_pidinfo if ps is unavailable.
    If the process no longer exists, returns 0.0 silently.
    Returns total CPU seconds consumed by the process.
    """
    # Pre-check: test if the process is still alive using signal 0
    # (which sends no actual signal but performs error-checking).
    # This avoids spawning ps subprocess or loading ctypes for a process
    # that already exited — a common case since CommandExecutor attaches
    # the throttler to every subprocess, including fast utility commands
    # (mv, mkdir, cp) that finish in milliseconds.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        # Process already exited — nothing to sample, return 0.0 silently.
        return 0.0
    except OSError:
        # Permission error or other OS-level issue — process may still
        # be alive. Fall through to normal sampling.
        pass

    try:
        return _macos_ps_fallback(pid)
    except (ProcessLookupError, ValueError, RuntimeError, subprocess.TimeoutExpired) as err:
        logger.debug('ps fallback to proc_pidinfo for pid %d: %s', pid, err)
        try:
            return _macos_proc_pidinfo(pid)
        except (ImportError, AttributeError, OSError) as fallback_err:
            logger.warning(
                'Both ps and proc_pidinfo failed for pid %d: %s',
                pid, fallback_err,
            )
            return 0.0


def _macos_proc_pidinfo(pid: int) -> float:
    """Use macOS proc_pidinfo API via ctypes."""
    import ctypes  # noqa: PLC0415
    import ctypes.util  # noqa: PLC0415

    libc = ctypes.CDLL(ctypes.util.find_library('c'))

    class ProcTaskInfo(ctypes.Structure):
        _fields_ = [
            ('pti_virtual_size', ctypes.c_uint64),
            ('pti_resident_size', ctypes.c_uint64),
            ('pti_total_user', ctypes.c_uint64),
            ('pti_total_system', ctypes.c_uint64),
            ('pti_threads_user', ctypes.c_uint64),
            ('pti_threads_system', ctypes.c_uint64),
            ('pti_policy', ctypes.c_int32),
            ('pti_faults', ctypes.c_int32),
            ('pti_pageins', ctypes.c_int32),
            ('pti_cow_faults', ctypes.c_int32),
            ('pti_messages_sent', ctypes.c_uint32),
            ('pti_messages_received', ctypes.c_uint32),
            ('pti_syscalls_mach', ctypes.c_uint32),
            ('pti_syscalls_unix', ctypes.c_uint32),
            ('pti_csw', ctypes.c_uint32),
            ('pti_threadnum', ctypes.c_int32),
            ('pti_numrunning', ctypes.c_int32),
            ('pti_priority', ctypes.c_int32),
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
        raise ProcessLookupError(f'proc_pidinfo failed for pid {pid}')

    total_ns = task_info.pti_total_user + task_info.pti_total_system
    return total_ns / 1e9


def _macos_ps_fallback(pid: int) -> float:
    """Fallback: parse ps output for utime+stime."""
    try:
        result = subprocess.run(
            ['ps', '-p', str(pid), '-o', 'utime=,stime='],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise ProcessLookupError(
                f'ps failed for pid {pid}: {result.stderr.strip()}'
            )
        parts = result.stdout.strip().split()
        if len(parts) < 2:
            raise ValueError(
                f'Unexpected ps output: {result.stdout.strip()!r}'
            )
        utime = _parse_ps_time(parts[0])
        stime = _parse_ps_time(parts[1])
        return utime + stime
    except FileNotFoundError as err:
        raise RuntimeError('ps command not found') from err


def _parse_ps_time(time_str: str) -> float:
    """Parse ps time format ([[DD-]hh:]mm:ss[.frac]) to seconds."""
    time_str = time_str.strip()
    total_seconds = 0.0
    if '-' in time_str:
        days_part, rest = time_str.split('-', 1)
        total_seconds += int(days_part) * 86400
        time_str = rest
    parts = time_str.split(':')
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
    if system == 'Linux':
        return linux_sample_cpu_time(pid)
    elif system == 'Darwin':
        return macos_sample_cpu_time(pid)
    else:
        raise NotImplementedError(f'Unsupported platform: {system}')


def system_cpu_load() -> float:
    """Return system-wide CPU load as percentage (0.0-100.0 per core)."""
    system = platform.system()
    if system == 'Linux':
        return _linux_system_load()
    elif system == 'Darwin':
        return _macos_system_load()
    else:
        raise NotImplementedError(f'Unsupported platform: {system}')


_LINUX_CPU_LAST = {'total': 0.0, 'idle': 0.0}
_LINUX_CPU_LOCK = threading.Lock()


def _linux_system_load() -> float:
    """Calculate CPU usage % from /proc/stat diffs."""
    global _LINUX_CPU_LAST  # noqa: PLW0603
    try:
        with open('/proc/stat') as f:
            parts = f.readline().split()
        total = sum(float(p) for p in parts[1:])
        idle = float(parts[4])
        with _LINUX_CPU_LOCK:
            last_total = _LINUX_CPU_LAST['total']
            last_idle = _LINUX_CPU_LAST['idle']
            _LINUX_CPU_LAST['total'] = total
            _LINUX_CPU_LAST['idle'] = idle
        if last_total == 0:
            return 0.0
        delta_total = total - last_total
        delta_idle = idle - last_idle
        if delta_total <= 0:
            return 0.0
        return (1.0 - delta_idle / delta_total) * 100.0
    except (OSError, IndexError, ValueError) as err:
        logger.warning('Failed to read /proc/stat: %s', err)
        return 0.0


def _macos_system_load() -> float:
    """Calculate CPU usage % from os.getloadavg() on macOS."""
    load1, _, _ = os.getloadavg()
    core_count = os.cpu_count() or 1
    return (load1 / core_count) * 100.0
