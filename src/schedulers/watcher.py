import logging
import os
import signal
import threading
import time
from concurrent.futures import Future
from functools import partial
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import CONFIG
from folder import Folder
from src.file.debounce import DebounceBuffer
from src.file.stability import FileStabilityTracker
from src.schemas import StateChoices
from utils import exceptions, file, response

logger = logging.getLogger()



def _parse_folder_file(filepath: str) -> list[str]:
    text = Path(filepath).read_text(encoding='utf-8')
    paths = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        paths.append(stripped)
    return paths


def _find_watch_folder_file() -> str | None:
    """Search for var/folder.sh: env var → cwd & parent dirs → tool source parent."""
    # 1. Env var override
    env_path = os.getenv('WATCH_FOLDER_FILE')
    if env_path:
        env_path = env_path.strip().strip('\'"')
        if os.path.isfile(env_path):
            return env_path
    # 2. Walk up from cwd
    start = os.path.abspath(os.getcwd())
    current = start
    while True:
        candidate = os.path.join(current, 'var', 'folder.sh')
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    # 3. Walk up from tool's config.py location (covers uv tool install from project root)
    import config as _cfg_mod

    current = os.path.dirname(os.path.abspath(_cfg_mod.__file__))
    while True:
        candidate = os.path.join(current, 'var', 'folder.sh')
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


class _WatchEventHandler(FileSystemEventHandler):
    def __init__(
        self, debounce_buffer: DebounceBuffer, stability_tracker: FileStabilityTracker
    ):
        self.debounce_buffer = debounce_buffer
        self.stability_tracker = stability_tracker

    def dispatch(self, event):
        if event.is_directory:
            return
        if event.event_type not in ('created', 'modified', 'moved'):
            return
        if event.event_type == 'moved':
            path = event.dest_path
        else:
            path = event.src_path
        if '/_[' in path or '/.removed/' in path:
            return
        logger.info(f'File event detected: {event.event_type} {path}')
        if self.stability_tracker.wait_until_stable(path):
            self.debounce_buffer.add(path)


def _batch_callback(future: Future):
    logger.debug('_batch_callback entered')
    try:
        result = future.result()
        logger.debug(
            '_batch_callback: future.result() type=%s, data=%s, result=%s',
            type(result).__name__,
            result.data if hasattr(result, 'data') else 'N/A',
            result,
        )
    except Exception as e:
        logger.warning(
            '_batch_callback: future.result() raised %s: %s', type(e).__name__, e
        )
        return
    if not hasattr(result, 'data') or result.data is None:
        logger.debug('_batch_callback: result.data is None or missing, early return')
        return
    media = result.data.get('media')
    if media is None:
        logger.error(
            '_batch_callback: result.data.get("media") returned None, data=%s',
            result.data,
        )
        return
    if result == 0:
        logger.debug('_batch_callback: SUCCESS, setting state to finished=2')
        try:
            media.model.update_state('compress', StateChoices.finished)
        except Exception as exc:
            logger.error(
                '_batch_callback: update_state(finished) raised %s: %s',
                type(exc).__name__,
                exc,
            )
        try:
            file.soft_remove(media.path)
            logger.debug('_batch_callback: soft_remove completed for %s', media.path)
        except Exception as exc:
            logger.error(
                '_batch_callback: soft_remove(%s) raised %s: %s',
                media.path,
                type(exc).__name__,
                exc,
            )
    else:
        logger.debug(
            '_batch_callback: FAILURE path (result=%s), setting state to failed=-2',
            result,
        )
        try:
            media.model.update_state('compress', StateChoices.failed)
        except Exception as exc:
            logger.error(
                '_batch_callback: update_state(failed) raised %s: %s',
                type(exc).__name__,
                exc,
            )


class WatcherScheduler:
    def __init__(self):
        self._stop_event = threading.Event()
        self.observer: Observer | None = None
        self.task_manager = None
        self._inflight_batch = threading.Event()
        self._flush_lock = threading.Lock()

    @staticmethod
    def _ensure_pid_dir() -> str:
        pid_dir = Path.home() / '.mediakit'
        try:
            pid_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        return str(pid_dir)

    def _write_pid_file(self):
        pid_dir = self._ensure_pid_dir()
        pid_path = Path(pid_dir) / 'daemon.pid'
        pid_path.write_text(str(os.getpid()))
        logger.info('PID file written to %s', pid_path)

    @staticmethod
    def _cleanup_pid_file():
        pid_path = Path.home() / '.mediakit' / 'daemon.pid'
        if pid_path.exists():
            pid_path.unlink()
            logger.info('PID file cleaned up: %s', pid_path)

    def _setup_cpu_throttling(self, cpu_limit: int | None):
        from src.schedulers.folder import _coordinator

        if isinstance(cpu_limit, str) and cpu_limit.isdigit():
            cpu_limit = int(cpu_limit)
        if isinstance(cpu_limit, int) and cpu_limit > 0:
            _coordinator.set_manual_override(cpu_limit)

    def _flush_callback(
        self,
        paths: list[str],
        media_type: str,
        max_workers: int,
        action: str = 'compress',
    ):
        with self._flush_lock:
            self._inflight_batch.set()
            try:
                folder = Folder(os.path.dirname(paths[0]) if paths else '.')
                medias = []
                for path in paths:
                    try:
                        medias.append(folder.MEDIA_CLS(path))
                    except exceptions.NotMediaException:
                        logger.warning('Ignoring non-media file during watch: %s', path)
                if not medias:
                    return
                try:
                    Folder.run__(
                        action,
                        medias=medias,
                        max_workers=max_workers,
                        callback_list=[_batch_callback],
                    )
                except Exception as exc:
                    logger.error('Batch processing failed: %s: %s', type(exc).__name__, exc)
            finally:
                self._inflight_batch.clear()

    def _setup_observer(
        self,
        path: str,
        recursive: bool,
        media_type: str,
        max_workers: int,
        action: str = 'compress',
    ):
        buffer = DebounceBuffer(
            calm_period=5.0,
            max_flush_interval=60.0,
            callback=partial(
                self._flush_callback,
                media_type=media_type,
                max_workers=max_workers,
                action=action,
            ),
        )
        tracker = FileStabilityTracker(
            sample_interval=1.0, stable_samples=3, timeout=30.0
        )
        handler = _WatchEventHandler(buffer, tracker)

        self.observer = Observer()
        self.observer.schedule(handler, path, recursive=recursive)
        self.observer.start()
        logger.info('Watching folder: %s (recursive=%s)', path, recursive)

    def _feed_existing(
        self, path: str, media_type: str, max_workers: int, action: str = 'compress'
    ):
        folder = Folder(path)
        folder.scan_media()
        query = folder.get_query_statement('QUERY_UNPROCESSED')
        result = folder.query(query)
        assert isinstance(result, response.Result)
        if result == 0 and result.data:
            medias = [folder.MEDIA_CLS(m.path) for m in result.data]
            try:
                Folder.run__(
                    action,
                    medias=medias,
                    max_workers=max_workers,
                    callback_list=[_batch_callback],
                )
            except Exception as exc:
                logger.error(
                    'Failed to process existing media: %s: %s', type(exc).__name__, exc
                )

    def _run_event_loop(self):
        while not self._stop_event.is_set():
            if self.observer and not self.observer.is_alive():
                logger.warning('Observer died, restarting...')
                self.observer.start()
            time.sleep(1)

    def _signal_handler(self, signum, frame):
        logger.info(f'Received signal {signum}, shutting down...')
        self._stop_event.set()
        if self.observer:
            self.observer.stop()
        if self._inflight_batch.is_set():
            logger.info('Waiting for in-flight media batch to complete...')
            self._inflight_batch.wait()
        if self.task_manager:
            self.task_manager.stop()

    def _setup_multi_observer(
        self,
        paths: list[str],
        recursive: bool,
        media_type: str,
        max_workers: int,
        action: str = 'compress',
    ):
        buffer = DebounceBuffer(
            calm_period=5.0,
            max_flush_interval=60.0,
            callback=partial(
                self._flush_callback,
                media_type=media_type,
                max_workers=max_workers,
                action=action,
            ),
        )
        tracker = FileStabilityTracker(
            sample_interval=1.0, stable_samples=3, timeout=30.0
        )
        handler = _WatchEventHandler(buffer, tracker)

        self.observer = Observer()
        for path in paths:
            self.observer.schedule(handler, path, recursive=recursive)
        self.observer.start()
        logger.info('Watching %d folders (recursive=%s)', len(paths), recursive)

    def core(self, **kwargs):
        folder_path = kwargs.get('folder', CONFIG.MEDIA_FILE_FOLDER)
        folder_file = kwargs.get('folder_file', None)
        media_type = kwargs.get('type', 'video')
        max_workers = kwargs.get('max_workers', CONFIG.MAX_WORKERS)
        cpu_limit = kwargs.get('cpu_limit', None)
        action = kwargs.get('action', 'compress')
        recursive = kwargs.get('recursive', False)
        no_scan_existing = kwargs.get('no_scan_existing', False)

        self._setup_cpu_throttling(cpu_limit)

        if folder_file is not None:
            raw_paths = _parse_folder_file(folder_file)
        elif folder_path == CONFIG.MEDIA_FILE_FOLDER:
            watch_file = _find_watch_folder_file()
            if watch_file:
                logger.debug('Using watch folder file: %s', watch_file)
                raw_paths = _parse_folder_file(watch_file)
            else:
                logger.warning(
                    'No var/folder.sh found from cwd (%s). '
                    'Either: (1) cd to project root and re-run, '
                    '(2) set WATCH_FOLDER_FILE env var, '
                    '(3) use -f DIR, or (4) use --folder-file FILE.',
                    os.getcwd(),
                )
                raw_paths = [folder_path]
        else:
            raw_paths = [folder_path]

        valid_paths = [p for p in raw_paths if os.path.isdir(p)]
        for p in raw_paths:
            if p not in valid_paths:
                logger.warning('Folder path does not exist, skipping: %s', p)

        if not valid_paths:
            if raw_paths:
                logger.info('No valid folder paths found in folder file')
            self._run_event_loop()
            logger.info('Watch session ended.')
            return

        if not no_scan_existing:
            logger.info('Scanning existing media files...')
            for p in valid_paths:
                self._feed_existing(p, media_type, max_workers, action)

        if len(valid_paths) == 1:
            self._setup_observer(
                valid_paths[0], recursive, media_type, max_workers, action
            )
        else:
            self._setup_multi_observer(
                valid_paths, recursive, media_type, max_workers, action
            )
        logger.info('Watch is running. Waiting for file changes...')

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._write_pid_file()
        try:
            self._run_event_loop()
        finally:
            self._cleanup_pid_file()

        logger.info('Watch session ended.')
