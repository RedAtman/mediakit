"""Locating and parsing the watched-folder list.

Shared by the watch scheduler and the dedupe scheduler. It lives in src/file/
rather than in either scheduler so that neither has to import the other's
private helpers (dedupe used to import the underscore-prefixed parser straight
out of the watcher module).
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger()

__all__ = ['collapse_nested', 'find_folder_file', 'parse_folder_file']

FOLDER_FILE_RELPATH = os.path.join('var', 'folder.sh')


def parse_folder_file(filepath: str) -> list[str]:
    """One path per line, '#' comments and blank lines skipped.

    路径会规范化 (~ 展开、去掉 tailing slash、折叠 ./ 和 //) 并去重:
    watch 模式下每个条目在 watchdog 里都是一个独立的 FSEvents emitter 线程,
    重复条目等于白烧一个线程和一条流.
    """
    text = Path(filepath).read_text(encoding='utf-8')
    paths: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        normalized = os.path.normpath(os.path.expanduser(stripped))
        if normalized in seen:
            continue
        seen.add(normalized)
        paths.append(normalized)
    return paths


def collapse_nested(paths: list[str]) -> list[str]:
    """丢掉已被其他条目覆盖的子目录.

    仅在 recursive=True 时可用: 非递归 watch 里父目录并不覆盖子目录.
    保持原有顺序, 便于日志与 _watched_paths 对比.
    """
    kept: list[str] = []
    for path in paths:
        prefix = path.rstrip(os.sep) + os.sep
        if any(other != path and prefix.startswith(other.rstrip(os.sep) + os.sep) for other in paths):
            continue
        kept.append(path)
    return kept


def _walk_up_for(relpath: str, start: str) -> str | None:
    """Return the nearest ancestor of `start` containing `relpath`, else None."""
    current = os.path.abspath(start)
    while True:
        candidate = os.path.join(current, relpath)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def find_folder_file() -> str | None:
    """Locate var/folder.sh: env var → cwd and ancestors → tool source ancestors."""
    env_path = os.getenv('WATCH_FOLDER_FILE')
    if env_path:
        # 允许 .env 里写成 VAR="path" 或 VAR='path'
        env_path = env_path.strip().strip('\'"')
        if os.path.isfile(env_path):
            return env_path

    found = _walk_up_for(FOLDER_FILE_RELPATH, os.getcwd())
    if found:
        return found

    # config.py 的位置而不是 cwd: 从项目根以外启动 (launchd / brew) 时 cwd 可能无关
    import config as _config

    return _walk_up_for(FOLDER_FILE_RELPATH, os.path.dirname(os.path.abspath(_config.__file__)))
