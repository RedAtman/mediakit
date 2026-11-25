from concurrent.futures import Future
from functools import partial
import glob
import logging
import os
from pathlib import Path
import signal
import threading
import time
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import CONFIG
from folder import Folder, make_media
from src.config_file import Resolver, find_config_file, load_settings
from src.file.debounce import DebounceBuffer
from src.file.paths import collapse_nested, find_folder_file, parse_folder_file
from src.file.stability import FileStabilityTracker
from utils import exceptions, response
from utils.media import MEDIA_CATEGORIES, guess

from .callbacks import mark_compress_outcome
from .media import COMPRESS_OPTS
from .media import compress as media_compress

logger = logging.getLogger()


def _include_categories(media_type: str) -> list[str]:
    """把 --type 翻成事件入口可接受的 guess() 类别.

    不走 Folder.media_cls(): 'all'/'image' 在 MEDIA_CLASSES 里没有实现类,
    而这里只需要"这个扩展名该不该进管道"的粗筛, 末级 flush 仍由 MEDIA_CLS 定调.
    认不出的类型放过所有媒体类别 —— 闸门宁可漏不可误杀.
    """
    if media_type in MEDIA_CATEGORIES:
        # 'image' 在 MEDIA_CLASSES 里还没有实现类, 放行到 flush 阶段只会换来一条
        # WARNING (Folder 默认按 video 判) —— 这里只做粗筛, 不为它能不能处理背书
        return [media_type]
    return list(MEDIA_CATEGORIES)


def _processing_media_type(media_type: str) -> str:
    """--type -> 具体 MEDIA_CLS 的名字. 'all'/'image' 还没有实现类, 沿用旧行为按 video 判."""
    return media_type if media_type in ('video', 'audio') else 'video'


class _WatchEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        debounce_buffer: DebounceBuffer,
        stability_tracker: FileStabilityTracker,
        categories_for: Callable[[str], list[str]] | None = None,
    ):
        self.debounce_buffer = debounce_buffer
        self.stability_tracker = stability_tracker
        # 同一轮 watch 里不同目录可以有不同的 --type, 所以类别是"按路径查"而不是整轮一个
        self._categories_for = categories_for or (lambda _path: list(MEDIA_CATEGORIES))

    def include_categories(self, path: str) -> list[str]:
        return list(self._categories_for(path))

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
        # 扩展名类别闸门: .DS_Store / ._xxx / --type 之外的扩展名在这里就出去.
        # 放行的话它们会先进 FileStabilityTracker (同步轮询阻塞 Observer 事件线程 ~3s),
        # 再进去抖缓冲, 直到 flush 阶段的类型判定才被拒.
        if guess(path) not in self._categories_for(path):
            return
        logger.info(f'File event detected: {event.event_type} {path}')
        if self.stability_tracker.wait_until_stable(path):
            self.debounce_buffer.add(path)


_thread_context = threading.local()


def _make_watched_task(scheduler, media, opts=None):
    """opts: 透传给 Video.compress 的参数 (resolution/fps), watch 模式下来自 CLI

    ponytail: 每次调用都重新解开 kwargs, 不做参数快照, 改 env 仍需重启 daemon
    """

    def task():
        _thread_context.current_path = media.path
        return scheduler(media, **(opts or {}))

    return task


class WatcherScheduler:
    # 未加载配置时的空 Resolver: 所有查询退回"整轮缺省", 行为与旧版一致.
    # 放在类上而不是 __init__, 是因为测试常用 object.__new__ 构造实例.
    _resolver: Resolver = Resolver()
    # config.toml 与旧的纯文本清单是两种解析器, mtime 轮询要分开处理
    _config_is_toml: bool = False
    # Video.compress 透传参数 (resolution/fps), 由 core() 按 CLI 覆盖; 默认空 = 全走 CONFIG 兜底
    _compress_opts: dict = {}

    @staticmethod
    def _normalize_path(path: str) -> str:
        try:
            return os.path.realpath(path)
        except (OSError, ValueError) as _:
            return os.path.abspath(path)

    def __init__(self):
        self._stop_event = threading.Event()
        self.observer: Observer | None = None
        self.task_manager = None
        self._inflight_batch = threading.Event()
        self._flush_lock = threading.Lock()
        self._processing_files: set[str] = set()
        self._processing_lock = threading.Lock()

        # Dynamic config file watch state
        self._handler: _WatchEventHandler | None = None
        self._config_filepath: str | None = None
        self._config_mtime: float | None = None
        self._config_poll_interval: float = 5.0
        self._last_config_check: float = 0.0
        self._watched_paths: set[str] = set()
        self._path_to_watch: dict[str, object] = {}
        # Watcher parameter cache (set during core())
        self._recursive: bool = False
        self._media_type: str = 'video'
        self._max_workers: int = 1
        # self._action: str = 'compress'  # unused; kept for future extensibility

    def _batch_callback(self, future: Future):
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
            logger.warning('_batch_callback: future.result() raised %s: %s', type(e).__name__, e)
            current_path = getattr(_thread_context, 'current_path', None)
            if current_path is not None:
                _thread_context.current_path = None
            with self._processing_lock:
                if current_path is not None:
                    self._processing_files.discard(current_path)
            return
        if not hasattr(result, 'data') or result.data is None:
            logger.debug('_batch_callback: result.data is None or missing, early return')
            current_path = getattr(_thread_context, 'current_path', None)
            if current_path is not None:
                _thread_context.current_path = None
            with self._processing_lock:
                if current_path is not None:
                    self._processing_files.discard(current_path)
            return
        media = result.data.get('media')
        if media is None:
            logger.error('_batch_callback: result.data.get("media") returned None, data=%s', result.data)
            current_path = getattr(_thread_context, 'current_path', None)
            if current_path is not None:
                _thread_context.current_path = None
            with self._processing_lock:
                if current_path is not None:
                    self._processing_files.discard(current_path)
            return
        # Always cleanup thread-local and processing set
        current_path = getattr(_thread_context, 'current_path', None)
        if current_path is not None:
            _thread_context.current_path = None
        with self._processing_lock:
            if current_path is not None:
                self._processing_files.discard(current_path)
            if hasattr(media, 'path'):
                normalized_media_path = self._normalize_path(media.path)
                if normalized_media_path != current_path:
                    self._processing_files.discard(normalized_media_path)
        mark_compress_outcome(result)

    @staticmethod
    def _ensure_pid_dir() -> str:
        pid_dir = Path.home() / '.mediakit'
        try:
            pid_dir.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        return str(pid_dir)

    @staticmethod
    def _read_live_pid(pid_path: Path) -> int | None:
        """pid 文件里指向的存活进程, 没有/陈旧/不可解析都返回 None."""
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

    def _ensure_single_instance(self):
        """已有 daemon 存活就拒绝启动.

        单实例保护原先只存在于 watcher_.sh 的 pgrep 里; 脚本删掉后必须由应用自己守:
        两个 daemon 同时盯同一批目录会把同一份文件压两遍.
        """
        pid_path = Path(self._ensure_pid_dir()) / 'daemon.pid'
        live = self._read_live_pid(pid_path)
        if live is not None:
            raise SystemExit(f'watch daemon already running (PID {live}); run `mediakit stop` first')

    def _write_pid_file(self):
        pid_dir = self._ensure_pid_dir()
        pid_path = Path(pid_dir) / 'daemon.pid'
        try:
            # O_EXCL: 早先的 liveness 检查与写入之间仍有窗口, 两个进程可能同时通过检查
            fd = os.open(pid_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            live = self._read_live_pid(pid_path)
            if live is not None:
                raise SystemExit(f'watch daemon already running (PID {live}); run `mediakit stop` first') from None
            pid_path.unlink(missing_ok=True)  # 陈旧文件: 重来一次
            try:
                fd = os.open(pid_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            except FileExistsError:
                # 极端竞态: 另一进程在同一瞬间抢到了; 不要带着 traceback 崩
                raise SystemExit('watch daemon is starting up concurrently; retry in a moment') from None
        with os.fdopen(fd, 'w') as handle:
            handle.write(str(os.getpid()))
        logger.info('PID file written to %s', pid_path)

    @staticmethod
    def _cleanup_pid_file():
        pid_path = Path.home() / '.mediakit' / 'daemon.pid'
        if pid_path.exists():
            pid_path.unlink()
            logger.info('PID file cleaned up: %s', pid_path)

    def _setup_cpu_throttling(self, cpu_limit: int | None):
        from src.schedulers.folder import coordinator

        if isinstance(cpu_limit, str) and cpu_limit.isdigit():
            cpu_limit = int(cpu_limit)
        # 同上: watch 模式也必须先把协调器建出来, 否则 /tmp/mediakit_cpu_* 没人扫
        coord = coordinator()
        if isinstance(cpu_limit, int) and cpu_limit > 0:
            coord.set_manual_override(cpu_limit)

    def _flush_callback(self, paths: list[str], media_type: str, max_workers: int):
        with self._flush_lock:
            self._inflight_batch.set()
            try:
                with self._processing_lock:
                    normalized = [self._normalize_path(p) for p in paths]
                    new_paths = [p for p in normalized if p not in self._processing_files]
                    self._processing_files.update(new_paths)

                if not new_paths:
                    return

                try:
                    tasks = []
                    for path in new_paths:
                        try:
                            # 'image'/'all' 没有对应的 MEDIA_CLASSES 实现, 与旧行为一致按 video 判定
                            folder = Folder(
                                os.path.dirname(path),
                                _processing_media_type(self._resolver.media_type_for(path, media_type)),
                            )
                            media = folder.MEDIA_CLS(path)
                        except exceptions.NotMediaException:
                            with self._processing_lock:
                                self._processing_files.discard(self._normalize_path(path))
                            logger.warning('Ignoring non-media file during watch: %s', path)
                            continue
                        except Exception as err:
                            # 目录在事件与 flush 之间消失 (Folder 构造失败) 也不能连累同批文件
                            with self._processing_lock:
                                self._processing_files.discard(self._normalize_path(path))
                            logger.warning('Cannot build media, skipping for now: %s (%s)', path, err)
                            continue
                        try:
                            # 扩展名只能粗筛 (._foo.mp4 借了 .mp4 的扩展名); 真正的判定是 ffprobe.
                            # metadata 是 cached_property: 这里探到的结果会被后续 compress 复用,
                            # 不多花一个进程; 探不到就不建任务, 免得白跑一趟再记 failed.
                            media.metadata
                        except exceptions.NotMediaException as err:
                            with self._processing_lock:
                                self._processing_files.discard(self._normalize_path(path))
                            # 同上: 级别与原因由 get_metadata 打过了, 这里只留 trace
                            logger.debug('Not processable media, skipping task: %s (%s)', path, err.msg)
                            continue
                        except Exception as err:
                            # 探测报的其他异常 (如 ffprobe 输出解析不出) 不能连累同批文件:
                            # 跳过这一条, 它保持未处理状态, 下一轮还能再试
                            with self._processing_lock:
                                self._processing_files.discard(self._normalize_path(path))
                            logger.warning('Probe failed, skipping for now: %s (%s)', path, err)
                            continue
                        # 逐目录参数: media_type 决定用哪个 MEDIA_CLS, opts 覆盖 resolution/fps
                        tasks.append(
                            _make_watched_task(
                                media_compress.core, media, self._resolver.compress_opts_for(path, self._compress_opts)
                            )
                        )
                    if tasks:
                        Folder.run___(tasks=tasks, max_workers=max_workers, callback_list=[self._batch_callback])
                finally:
                    with self._processing_lock:
                        for path in new_paths:
                            self._processing_files.discard(self._normalize_path(path))
            finally:
                self._inflight_batch.clear()

    def _setup_observer(self, path: str, recursive: bool, media_type: str, max_workers: int):
        buffer = DebounceBuffer(
            calm_period=5.0,
            max_flush_interval=60.0,
            callback=partial(self._flush_callback, media_type=media_type, max_workers=max_workers),
        )
        tracker = FileStabilityTracker(sample_interval=1.0, stable_samples=3, timeout=30.0)
        handler = _WatchEventHandler(
            buffer,
            tracker,
            lambda event_path: _include_categories(self._resolver.media_type_for(event_path, media_type)),
        )
        self._handler = handler

        self.observer = Observer()
        watch = self.observer.schedule(handler, path, recursive=recursive)
        self._path_to_watch[path] = watch
        self.observer.start()
        logger.info('Watching folder: %s (recursive=%s)', path, recursive)

    def _feed_existing(self, path: str, media_type: str, max_workers: int):
        folder = Folder(path, media_type)
        folder.scan_media()
        query = folder.get_query_statement('QUERY_UNPROCESSED')
        result = folder.query(query)
        assert isinstance(result, response.Result)
        if result == 0 and result.data:
            with self._processing_lock:
                medias = []
                for m in result.data:
                    normalized = self._normalize_path(m.path)
                    if normalized not in self._processing_files:
                        medias.append(m)
                        self._processing_files.add(normalized)
            if not medias:
                return
            try:
                scheduler = media_compress.core
                tasks = []
                for m in medias:
                    # Fallback: if Media.path doesn't exist on disk, try glob with
                    # any extension. Handles legacy rows where the file was moved/renamed.
                    candidate = m.path
                    media = make_media(folder, candidate) if os.path.isfile(candidate) else None
                    if media is None:
                        # glob.escape protects against titles with [] and other regex-active chars
                        matches = glob.glob(f'{glob.escape(m.dirname)}/{glob.escape(m.title)}.*')
                        for match in matches:
                            if os.path.isfile(match):
                                media = make_media(folder, match)
                                if media is not None:
                                    break
                    if media is not None:
                        tasks.append(_make_watched_task(scheduler, media, self._compress_opts))
                Folder.run___(tasks=tasks, max_workers=max_workers, callback_list=[self._batch_callback])
            except Exception as exc:
                logger.error('Failed to process existing media: %s: %s', type(exc).__name__, exc)
                raise
            finally:
                with self._processing_lock:
                    for m in medias:
                        self._processing_files.discard(self._normalize_path(m.path))

    def _check_config_file_changes(self):
        """Poll WATCH_FOLDER_FILE for modifications and reconcile watched directories."""
        if not self._config_filepath:
            logger.debug('Config monitoring: _config_filepath is None, skipping')
            return

        if not os.path.isfile(self._config_filepath):
            logger.info('Config file missing (was it deleted?): %s', self._config_filepath)
            return

        try:
            current_mtime = os.path.getmtime(self._config_filepath)
        except OSError:
            logger.warning('Failed to read mtime for config file: %s', self._config_filepath)
            return

        if current_mtime == self._config_mtime:
            logger.debug('Config monitoring: mtime unchanged (%s), skipping', self._config_mtime)
            return

        logger.info('Config monitoring: mtime changed %s -> %s', self._config_mtime, current_mtime)

        try:
            if self._config_is_toml:
                # 改了 TOML: 重新加载, 同时刷新 resolver, 让 resolution/fps 的改动对新事件生效.
                # recursive 的改动要重新 schedule, 属于重启才生效的项 (见 README).
                settings = load_settings(self._config_filepath)
                self._resolver = settings.resolver()
                raw_paths = self._resolver.paths()
            else:
                raw_paths = parse_folder_file(self._config_filepath)
        except Exception as exc:
            logger.warning('Failed to parse config file %s: %s. Keeping current watches.', self._config_filepath, exc)
            return

        new_valid = {p for p in raw_paths if os.path.isdir(p)}
        for p in raw_paths:
            if p not in new_valid:
                logger.warning('New config path does not exist, skipping: %s', p)

        old = self._watched_paths
        to_remove = old - new_valid
        to_add = new_valid - old

        if not to_remove and not to_add:
            logger.debug(
                'Config monitoring: mtime changed but no path diff (file content same), updating mtime tracking only'
            )
            self._config_mtime = current_mtime
            return

        logger.info('Config monitoring: applying change: remove=%s, add=%s', to_remove, to_add)

        if self.observer is None:
            # No observer at startup means no path was valid at startup. If any
            # are now valid, install the observer and feed them. Otherwise just
            # sync state.
            if to_add:
                logger.info(
                    'Config monitoring: observer was not initialized at startup; installing now for %d new path(s)',
                    len(to_add),
                )
                self._setup_multi_observer(sorted(to_add), self._recursive, self._media_type, self._max_workers)
                for path in to_add:
                    self._feed_existing(path, self._media_type, self._max_workers)
            else:
                logger.info('Config monitoring: observer not initialized and no new valid paths; nothing to do')
            for path in to_remove:
                self._path_to_watch.pop(path, None)
                self._watched_paths.discard(path)
            self._watched_paths.update(to_add)
            self._config_mtime = current_mtime
            return

        for path in to_remove:
            if path in self._path_to_watch:
                watch = self._path_to_watch.pop(path)
                self.observer.unschedule(watch)
                self._watched_paths.discard(path)
                logger.info('Stopped watching (removed from config): %s', path)

        for path in to_add:
            if not os.path.isdir(path):
                logger.warning('Cannot watch new config path (not a directory): %s', path)
                continue
            path_recursive = self._resolver.recursive_for(path, self._recursive)
            watch = self.observer.schedule(self._handler, path, recursive=path_recursive)
            self._path_to_watch[path] = watch
            self._watched_paths.add(path)
            logger.info('Started watching (added from config): %s (recursive=%s)', path, path_recursive)
            self._feed_existing(
                path, _processing_media_type(self._resolver.media_type_for(path, self._media_type)), self._max_workers
            )

        self._config_mtime = current_mtime

    def _run_event_loop(self):
        while not self._stop_event.is_set():
            if self.observer and not self.observer.is_alive():
                logger.warning('Observer died, restarting...')
                self.observer.start()
            now = time.time()
            if now - self._last_config_check >= self._config_poll_interval:
                self._check_config_file_changes()
                self._last_config_check = now
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

    def _setup_multi_observer(self, paths: list[str], recursive: bool, media_type: str, max_workers: int):
        buffer = DebounceBuffer(
            calm_period=5.0,
            max_flush_interval=60.0,
            callback=partial(self._flush_callback, media_type=media_type, max_workers=max_workers),
        )
        tracker = FileStabilityTracker(sample_interval=1.0, stable_samples=3, timeout=30.0)
        handler = _WatchEventHandler(
            buffer,
            tracker,
            lambda event_path: _include_categories(self._resolver.media_type_for(event_path, media_type)),
        )
        self._handler = handler

        # New Observer + clear stale state so the dict matches what this Observer
        # actually schedules (callers may pass a subset when adding late paths).
        self.observer = Observer()
        self._path_to_watch.clear()
        for path in paths:
            path_recursive = self._resolver.recursive_for(path, recursive)
            watch = self.observer.schedule(handler, path, recursive=path_recursive)
            self._path_to_watch[path] = watch
        self.observer.start()
        logger.info('Watching %d folders (recursive default=%s)', len(paths), recursive)

    def _resolve_config_paths(self, configured: list[str], recursive: bool):
        """config.toml 声明的目录: 过滤不存在项, 只对 recursive 的子树折叠嵌套.

        非递归时每个目录是独立身份, 不能折叠 (见 AGENTS.md 的 watcher 不变量).
        """
        valid_paths = [p for p in configured if os.path.isdir(p)]
        missing = [p for p in configured if p not in valid_paths]
        if missing:
            logger.warning('%d of %d configured folders do not exist: %s', len(missing), len(configured), missing[:5])

        recursive_paths = [p for p in valid_paths if self._resolver.recursive_for(p, recursive)]
        if recursive_paths:
            collapsed = collapse_nested(recursive_paths)
            if len(collapsed) != len(recursive_paths):
                logger.info('Recursive watch: collapsed %d nested path(s)', len(recursive_paths) - len(collapsed))
            valid_paths = [p for p in valid_paths if p not in recursive_paths] + collapsed
        return configured, valid_paths

    @staticmethod
    def _resolve_watch_paths(folder_path: str, folder_file: str | None, recursive: bool):
        """Resolve --folder-file / -f DIR / the default folder list into watch paths.

        Returns (raw_paths as configured, existing paths to watch, the config file
        being monitored or None). Kept out of core() because core() is the run loop
        orchestrator and this is pure input resolution.
        """
        config_filepath: str | None = None
        if folder_file is not None:
            raw_paths = parse_folder_file(folder_file)
            config_filepath = folder_file
        elif folder_path == CONFIG.MEDIA_FILE_FOLDER:
            watch_file = find_folder_file()
            if watch_file:
                logger.debug('Using watch folder file: %s', watch_file)
                raw_paths = parse_folder_file(watch_file)
                config_filepath = watch_file
            else:
                logger.warning(
                    'No folder list found from cwd (%s). '
                    'Either: (1) create ~/.config/mediakit/config.toml, '
                    '(2) create ~/.config/mediakit/folders.txt, '
                    '(3) set WATCH_FOLDER_FILE, (4) use -f DIR, or (5) use --folder-file FILE.',
                    os.getcwd(),
                )
                raw_paths = [folder_path]
        else:
            # 单个 -f DIR 模式, 没有配置文件可监控
            raw_paths = [folder_path]

        valid_paths = [p for p in raw_paths if os.path.isdir(p)]
        for p in raw_paths:
            if p not in valid_paths:
                logger.warning('Folder path does not exist, skipping: %s', p)

        # 递归 watch 下子目录已被父目录覆盖, 多一条就多一个 emitter 线程与 FSEvents 流
        if recursive:
            collapsed = collapse_nested(valid_paths)
            if len(collapsed) != len(valid_paths):
                logger.info('Recursive watch: collapsed %d nested path(s)', len(valid_paths) - len(collapsed))
            valid_paths = collapsed

        return raw_paths, valid_paths, config_filepath

    def core(self, **kwargs):
        folder_path = kwargs.get('folder', CONFIG.MEDIA_FILE_FOLDER)
        folder_file = kwargs.get('folder_file', None)
        config_path = kwargs.get('config', None)
        media_type = kwargs.get('type', 'video')
        max_workers = kwargs.get('max_workers', CONFIG.MAX_WORKERS)
        # action = kwargs.get('action', 'compress')  # unused; kept for future extensibility
        recursive = kwargs.get('recursive', False)
        no_scan_existing = kwargs.get('no_scan_existing', False)

        self._ensure_single_instance()

        # 配置非法就让进程 Failed fast: 静默忽略一个写错的 key 比拒绝启动更糟
        settings = load_settings(config_path)
        self._resolver = settings.resolver()
        # CLI -c 优先于 config 里的 watch.cpu_limit 优先于环境/CONFIG
        cpu_limit = kwargs.get('cpu_limit') or settings.watch.cpu_limit

        self._setup_cpu_throttling(cpu_limit)

        if not self._resolver.paths() and find_config_file(config_path) is not None:
            logger.warning(
                'Config file declares no [[watch.folders]]; falling back to --folder-file/-f. '
                'Add folders there, or delete the file to silence this.'
            )
        if self._resolver.paths():
            config_filepath = str(find_config_file(config_path) or '')
            self._config_is_toml = True
            raw_paths, valid_paths = self._resolve_config_paths(self._resolver.paths(), recursive)
        else:
            # 同一进程内二次 core() 时, 上一次的 TOML 标志必须清掉, 否则热重载会拿纯文本
            # 清单去 TOML 解析
            self._config_is_toml = False
            raw_paths, valid_paths, config_filepath = self._resolve_watch_paths(folder_path, folder_file, recursive)

        # --- State initialization for dynamic config monitoring ---
        self._watched_paths = set(valid_paths)
        self._media_type = media_type
        self._max_workers = max_workers
        # 只白名单透传 Video.compress 认的参数, watch 模式下 CLI 显式指定时以 CLI 为准
        self._compress_opts = {key: kwargs[key] for key in COMPRESS_OPTS if kwargs.get(key) is not None}
        # self._action = action  # unused; kept for future extensibility
        self._recursive = recursive
        self._config_filepath = config_filepath
        # Initialize mtime if config file exists
        if self._config_filepath and os.path.isfile(self._config_filepath):
            self._config_mtime = os.path.getmtime(self._config_filepath)
            logger.info(
                'Config monitoring: active (file=%s, mtime=%s, poll=%ss)',
                self._config_filepath,
                self._config_mtime,
                self._config_poll_interval,
            )
        else:
            logger.info(
                'Config monitoring: inactive (config file not found at %s)',
                self._config_filepath if self._config_filepath else 'N/A',
            )
        # --- END state initialization ---

        if not valid_paths:
            if raw_paths:
                logger.info('No valid folder paths found in folder file')
            self._watched_paths = set()
            self._run_event_loop()
            logger.info('Watch session ended.')
            return

        if not no_scan_existing:
            logger.info('Scanning existing media files...')
            for p in valid_paths:
                self._feed_existing(
                    p, _processing_media_type(self._resolver.media_type_for(p, media_type)), max_workers
                )

        if len(valid_paths) == 1:
            self._setup_observer(
                valid_paths[0], self._resolver.recursive_for(valid_paths[0], recursive), media_type, max_workers
            )
        else:
            self._setup_multi_observer(valid_paths, recursive, media_type, max_workers)
        logger.info('Watch is running. Waiting for file changes...')

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._write_pid_file()
        try:
            self._run_event_loop()
        finally:
            self._cleanup_pid_file()

        logger.info('Watch session ended.')
