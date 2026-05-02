from concurrent.futures import Future
from functools import partial
import logging
import os
import signal
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import CONFIG
from folder import Folder
from src.file.debounce import DebounceBuffer
from src.file.stability import FileStabilityTracker
from utils import file, response


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


class _WatchEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        debounce_buffer: DebounceBuffer,
        stability_tracker: FileStabilityTracker,
    ):
        self.debounce_buffer = debounce_buffer
        self.stability_tracker = stability_tracker

    def dispatch(self, event):
        if event.is_directory:
            return
        if event.event_type != 'created':
            return
        path = event.src_path
        if '/_[' in path or '/.removed/' in path:
            return
        logger.debug(f'File created: {path}')
        if self.stability_tracker.wait_until_stable(path):
            self.debounce_buffer.add(path)


def _batch_callback(future: Future):
    try:
        result = future.result()
    except Exception as e:
        logger.warning('Compression failed: %s', e)
        return
    if not isinstance(result, dict):
        return
    new_file_path = result.get('new_file_path')
    if new_file_path and os.path.exists(new_file_path):
        media = result['media']
        file.soft_remove(media.path)


class WatcherScheduler:
    def __init__(self):
        self._stop_event = threading.Event()
        self.observer: Observer | None = None
        self.task_manager = None

    def _setup_cpu_throttling(self, cpu_limit: int | None):
        from src.schedulers.folder import _coordinator
        if isinstance(cpu_limit, str) and cpu_limit.isdigit():
            cpu_limit = int(cpu_limit)
        if isinstance(cpu_limit, int) and cpu_limit > 0:
            _coordinator.set_manual_override(cpu_limit)

    def _flush_callback(self, paths: list[str], media_type: str, max_workers: int):
        folder = Folder(os.path.dirname(paths[0]) if paths else '.')
        medias = [folder.MEDIA_CLS(path) for path in paths]
        Folder.run__(
            'compress',
            medias=medias,
            max_workers=max_workers,
            callback_list=[_batch_callback],
        )

    def _setup_observer(
        self,
        path: str,
        recursive: bool,
        media_type: str,
        max_workers: int,
    ):
        buffer = DebounceBuffer(
            calm_period=5.0,
            max_flush_interval=60.0,
            callback=partial(
                self._flush_callback,
                media_type=media_type,
                max_workers=max_workers,
            ),
        )
        tracker = FileStabilityTracker(
            sample_interval=1.0,
            stable_samples=3,
            timeout=30.0,
        )
        handler = _WatchEventHandler(buffer, tracker)

        self.observer = Observer()
        self.observer.schedule(handler, path, recursive=recursive)
        self.observer.start()

    def _feed_existing(self, path: str, media_type: str, max_workers: int):
        folder = Folder(path)
        folder.scan_media()
        query = folder.get_query_statement('QUERY_UNPROCESSED')
        result = folder.query(query)
        assert isinstance(result, response.Result)
        if result == 0 and result.data:
            medias = [folder.MEDIA_CLS(m.path) for m in result.data]
            Folder.run__(
                'compress',
                medias=medias,
                max_workers=max_workers,
                callback_list=[_batch_callback],
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
        if self.task_manager:
            self.task_manager.stop()

    def _setup_multi_observer(
        self,
        paths: list[str],
        recursive: bool,
        media_type: str,
        max_workers: int,
    ):
        buffer = DebounceBuffer(
            calm_period=5.0,
            max_flush_interval=60.0,
            callback=partial(
                self._flush_callback,
                media_type=media_type,
                max_workers=max_workers,
            ),
        )
        tracker = FileStabilityTracker(
            sample_interval=1.0,
            stable_samples=3,
            timeout=30.0,
        )
        handler = _WatchEventHandler(buffer, tracker)

        self.observer = Observer()
        for path in paths:
            self.observer.schedule(handler, path, recursive=recursive)
        self.observer.start()

    def core(self, **kwargs):
        folder_path = kwargs.get('folder', CONFIG.MEDIA_FILE_FOLDER)
        folder_file = kwargs.get('folder_file', None)
        media_type = kwargs.get('type', 'video')
        max_workers = kwargs.get('max_workers', CONFIG.MAX_WORKERS)
        cpu_limit = kwargs.get('cpu_limit', None)
        recursive = not kwargs.get('no_recursive', False)
        no_scan_existing = kwargs.get('no_scan_existing', False)

        self._setup_cpu_throttling(cpu_limit)

        if folder_file is not None:
            raw_paths = _parse_folder_file(folder_file)
        elif folder_path == CONFIG.MEDIA_FILE_FOLDER and os.path.isfile(CONFIG.WATCH_FOLDER_FILE):
            raw_paths = _parse_folder_file(CONFIG.WATCH_FOLDER_FILE)
        else:
            logger.debug('WATCH_FOLDER_FILE not found, using MEDIA_FILE_FOLDER')
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

        if len(valid_paths) == 1:
            self._setup_observer(valid_paths[0], recursive, media_type, max_workers)
        else:
            self._setup_multi_observer(valid_paths, recursive, media_type, max_workers)

        if not no_scan_existing:
            for p in valid_paths:
                self._feed_existing(p, media_type, max_workers)

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._run_event_loop()

        logger.info('Watch session ended.')
