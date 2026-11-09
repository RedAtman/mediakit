"""Deduplicate media files by md5 content hash.

Two files sharing an md5 are the same content under different names. This
module finds those duplicates across the watched folders and moves the
extra copies to the macOS Trash (recoverable), keeping the one that matches
the DB record so the media table stays consistent.

CLI entry: mediakit dedupe [--apply] [--folder-file <path>] [--db <path>]
Default is a dry-run; --apply performs the actual removal.
"""

import logging
import os
from pathlib import Path
import sqlite3
import subprocess

from src.file.paths import find_folder_file, parse_folder_file
from utils.file import calculate_md5
from utils.media import guess

logger = logging.getLogger()

MEDIA_CATEGORIES = ('video', 'audio', 'image')

__all__ = ['dedupe']


def _send_to_trash(path: str) -> None:
    """Move a file to the macOS Trash via Finder so it stays recoverable."""
    subprocess.run(['osascript', '-e', f'tell application "Finder" to delete POSIX file "{path}"'], check=False)


def _collect_duplicates(folder_file: str, db_path: str) -> list[tuple[str, list[str]]]:
    """Return [(kept_path, [duplicate_paths])] for media files sharing an md5."""
    dirs = [d for d in parse_folder_file(folder_file) if os.path.isdir(d)]
    by_md5: dict[str, list[str]] = {}
    for d in dirs:
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for entry in entries:
            fp = os.path.join(d, entry)
            if not os.path.isfile(fp) or guess(entry) not in MEDIA_CATEGORIES:
                continue
            md5 = calculate_md5(fp)
            # Same folder listed twice in folder.sh would add the same path twice
            if fp not in by_md5.setdefault(md5, []):
                by_md5[md5].append(fp)

    # Prefer the DB-recorded path as survivor so the media table stays consistent
    db_known: dict[str, tuple[str, str]] = {}
    if os.path.isfile(db_path):
        conn = sqlite3.connect(db_path)
        for md5, title, dirname in conn.execute('SELECT md5, title, dirname FROM media'):
            db_known[md5] = (title, dirname)
        conn.close()

    result: list[tuple[str, list[str]]] = []
    for md5, paths in by_md5.items():
        if len(paths) < 2:
            continue
        known = db_known.get(md5)
        if known:
            survivors = [p for p in paths if os.path.join(known[1], known[0]) == p]
            kept = survivors[0] if survivors else paths[0]
        else:
            kept = paths[0]
        result.append((kept, [p for p in paths if p != kept]))
    return result


def dedupe(**kwargs) -> None:
    """Scan watched folders and move duplicate-media copies to Trash.

    Args:
        folder_file: Path to the folder list file (default: watcher resolution).
        db: Path to the media database (default: ./db.db).
        apply: When truthy, move duplicates to Trash; otherwise dry-run.
    """
    folder_file = kwargs.get('folder_file') or find_folder_file() or str(Path('var/folder.sh'))
    db_path = os.path.abspath(kwargs.get('db') or 'db.db')
    apply = bool(kwargs.get('apply'))
    duplicates = _collect_duplicates(folder_file, db_path)

    if not duplicates:
        logger.info('No duplicate media files found.')
        return

    total_freed = 0
    removed = 0
    for kept, dupes in duplicates:
        for d in dupes:
            size = os.path.getsize(d)
            total_freed += size
            removed += 1
            action = 'REMOVE' if apply else 'DRY-RUN'
            print(f'[{action}] {os.path.relpath(d)} ({size / 1024 / 1024:.0f}MB)')
            print(f'        keep: {os.path.relpath(kept)}')
            if apply:
                _send_to_trash(d)
    print(
        f'\n{"Removed" if apply else "Would remove"} {removed} duplicate(s), ~{total_freed / 1024 / 1024:.0f}MB freed.'
    )
    if not apply:
        print('Dry-run only. Re-run with --apply to move duplicates to Trash.')
