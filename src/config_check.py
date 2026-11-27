"""Read-only health report for the watch configuration (`mediakit --check-config`).

The configuration is a hand-edited file listing hundreds of folders, so "what did I
actually configure?" is a question the app should answer without starting a daemon.
Nothing here changes state: it only counts, resolves and estimates.
"""

import os

from config import CONFIG
from src.config_file import Settings, find_config_file
from src.file.paths import collapse_nested, find_folder_file, parse_folder_file

__all__ = ['build_report']

# 实测系数, 出处见 AGENTS.md 的 WATCHER INVARIANTS 表: 每条路径一个 FSEvents emitter,
# 约 33 KB 线程栈 + 一条内核流 + ~9 个 fd, 且创建是串行的 (~95 ms/条).
EST_BYTES_PER_STREAM = 33 * 1024
EST_FDS_PER_STREAM = 9
EST_MS_PER_STREAM = 95
MAX_MISSING_SHOWN = 5


def _resolve(paths_from_config: list[str], folder_file: str | None) -> tuple[list[str], str]:
    """Folders this install would watch, plus where they came from (same order as watch)."""
    if paths_from_config:
        return paths_from_config, 'config'
    if folder_file:
        return parse_folder_file(folder_file), folder_file
    found = find_folder_file()
    if found:
        return parse_folder_file(found), found
    return [], 'none'


def build_report(settings: Settings, config_path: str | None = None, folder_file: str | None = None) -> str:
    resolver = settings.resolver()
    paths, source = _resolve(resolver.paths(), folder_file)

    lines: list[str] = []
    # 调用方传进来的就是它实际加载的那份; 没传才去解析默认位置
    resolved = config_path or find_config_file(None)
    lines.append(f'config: {resolved or "(none found — using -f / --folder-file only)"}')

    if not paths:
        lines.append('folders: none — a watch run would fail with "nothing to watch"')
    else:
        # 先按规范路径去重: 否则 "entries 2 / usable 2 / duplicates 1" 这种自相矛盾的
        # 数字会同时出现在报告里
        unique: list[str] = []
        seen: set[str] = set()
        for path in paths:
            canonical_path = os.path.realpath(path)
            if canonical_path in seen:
                continue
            seen.add(canonical_path)
            unique.append(path)
        duplicates = len(paths) - len(unique)
        paths = unique

        valid = [p for p in paths if os.path.isdir(p)]
        missing = [p for p in paths if p not in valid]
        recursive = [p for p in valid if resolver.recursive_for(p, False)]
        collapsed = collapse_nested(recursive) if recursive else []

        origin = {'config': '[[watch.folders]] + folders_file', 'none': 'nothing'}.get(source, source)
        lines.append(f'folders from: {origin}')
        lines.append(f'  entries  : {len(paths)} (after de-duplication)')
        lines.append(f'  usable   : {len(valid)}')
        lines.append(f'  missing  : {len(missing)}')
        for path in missing[:MAX_MISSING_SHOWN]:
            lines.append(f'    - {path}')
        if len(missing) > MAX_MISSING_SHOWN:
            lines.append(f'    … {len(missing) - MAX_MISSING_SHOWN} more')
        if duplicates:
            lines.append(f'  duplicates collapsed: {duplicates}')
        if recursive:
            lines.append(f'  recursive entries: {len(recursive)} → collapsed to {len(collapsed)} watch(es)')

        watch_count = len([p for p in valid if p not in recursive]) + len(collapsed)
        mb = watch_count * EST_BYTES_PER_STREAM / 1024 / 1024
        plural = '' if watch_count == 1 else 's'
        lines.append(
            f'  estimate : {watch_count} FSEvents stream{plural} ≈ {watch_count} thread{plural}, '
            f'~{mb:.1f} MB stacks, ~{watch_count * EST_FDS_PER_STREAM} fds, '
            f'~{watch_count * EST_MS_PER_STREAM / 1000:.1f}s to schedule (serial)'
        )

    watch = settings.watch
    compress = settings.compress
    env_cpu = os.getenv('CPU_LIMIT')
    cpu_note = f' (env CPU_LIMIT={env_cpu} wins)' if env_cpu else f' (CONFIG.CPU_LIMIT={CONFIG.CPU_LIMIT})'
    lines.append(f'cpu_limit: {watch.cpu_limit if watch.cpu_limit is not None else "unset"}{cpu_note}')
    fps = compress.fps if compress.fps is not None else f'CONFIG.COMPRESS_FPS={CONFIG.COMPRESS_FPS}'
    resolution = compress.resolution
    if resolution is None:
        resolution = f'CONFIG.COMPRESS_RESOLUTION={CONFIG.COMPRESS_RESOLUTION}'
    lines.append(f'compress : fps={fps} resolution={resolution}')

    declared_db = settings.database.path
    env_db = os.getenv('SQLITE_DATABASE')
    if env_db:
        db_line = f'{CONFIG.SQLITE_DATABASE} (env SQLITE_DATABASE wins'
        if declared_db and declared_db != CONFIG.SQLITE_DATABASE:
            db_line += f'; [database] path {declared_db} ignored'
        db_line += ')'
    else:
        db_line = declared_db or f'{CONFIG.SQLITE_DATABASE} (default)'
    lines.append(f'database : {db_line}')
    lines.append(
        'note     : this report describes the config file; CLI flags (-f/--recursive/-c/--resolution) are not folded in'
    )

    return '\n'.join(lines)
