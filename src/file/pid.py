"""The daemon pid file: one place that owns its path, liveness and cleanup rules.

Two consumers depend on it and previously each rebuilt the path by hand:
`WatcherScheduler` (write on start, read for the single-instance guard) and
`mediakit stop` (read to signal the daemon). Drifting copies meant a test could
delete the real file out from under a running daemon.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger()

__all__ = ['PID_DIR_ENV', 'daemon_pid_path', 'read_live_pid']

# 容器 / 测试用: 指向别处就不必碰 ~/.mediakit
PID_DIR_ENV = 'MEDIAKIT_PID_DIR'


def daemon_pid_path() -> Path:
    base = os.getenv(PID_DIR_ENV) or os.path.join(os.path.expanduser('~'), '.mediakit')
    return Path(base) / 'daemon.pid'


def read_live_pid(pid_path: Path) -> int | None:
    """pid 文件指向的存活进程; 缺失/不可解析/陈旧/就是自己时返回 None."""
    try:
        pid = int(pid_path.read_text().strip())
    except OSError, ValueError:
        return None
    if pid == os.getpid():
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None  # 陈旧 pid 文件
    except PermissionError:
        return pid  # 存在但属于别人: 仍然占用
    return pid
