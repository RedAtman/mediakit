from concurrent.futures import Future
from functools import partial
import logging
import os as _os
from pathlib import Path as _Path
import signal as _signal
from typing import Any

from config import CONFIG
from folder import Folder, make_media
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from utils import file, response
from utils.command import CommandExecutor
from utils.throttle import CPULimiterCoordinator

from .callbacks import mark_compress_outcome
from .media import compress as media_compress

# Global CPU throttling coordinator
_coordinator = CPULimiterCoordinator(default_limit=CONFIG.CPU_LIMIT, auto_mode=True)
CommandExecutor.coordinator = _coordinator


__all__ = [
    'compress',
    'scale',
    'change_file_extension',
    'convert_format',
    'save_text',
    'combine',
    'reverse',
    'decode',
    'delete_voice',
    'save_metadata',
    'set_metadata',
    'images_to_video',
    'concat',
    'watch',
    'stop',
    'dedupe',
]


logger = logging.getLogger()


def _scheduler(func):
    """Attach a .core attribute to a plain function so CLI dispatcher can call scheduler.core()."""
    func.core = func
    return func


def _config(*args: Any, ctx: Context, **kwargs: dict[str, Any]):
    cpu_limit = kwargs.pop('cpu_limit', None)
    if isinstance(cpu_limit, str) and cpu_limit.isdigit():
        cpu_limit = int(cpu_limit)
    if isinstance(cpu_limit, int) and cpu_limit > 0:
        _coordinator.set_manual_override(cpu_limit)
    logger.debug(CONFIG.CPU_LIMIT)
    return ctx.next(*args, **kwargs)


def _scan(*args: Any, ctx: Context, **kwargs: dict[str, Any]):
    _folder = kwargs.get('folder', CONFIG.MEDIA_FILE_FOLDER)
    assert isinstance(_folder, str), 'Expected a string for path, but got %s' % type(_folder).__name__
    try:
        folder = Folder(_folder)
    except FileNotFoundError:
        return
    folder.scan_media()
    kwargs['folder'] = folder
    return ctx.next(*args, **kwargs)


def _query(*args: Any, ctx: Context, folder: Folder, **kwargs: dict[str, Any]):
    QUERY_UNPROCESSED = folder.get_query_statement('QUERY_UNPROCESSED')
    if not isinstance(QUERY_UNPROCESSED, folder.VALID_QUERY_TYPE):
        raise ValueError('Invalid query statement')
    result = folder.query(QUERY_UNPROCESSED)
    assert isinstance(result, response.Result)
    assert result == 0
    assert result == 'Success'
    medias = []
    for media in result.data:
        constructed = make_media(folder, media.path)
        if constructed is not None:
            medias.append(constructed)
    return ctx.next(*args, medias=medias, **kwargs)


def _callback(future: Future, *args, **kwargs):
    logger.debug('_callback entered, args=%s, kwargs=%s', args, kwargs)
    try:
        result = future.result()
        logger.debug(
            '_callback: future.result() type=%s, data=%s, result=%s',
            type(result).__name__,
            result.data if hasattr(result, 'data') else 'N/A',
            result,
        )
    except Exception as exc:
        logger.error('_callback: future.result() raised %s: %s', type(exc).__name__, exc)
        return
    if result.data is None:
        logger.debug('_callback: result.data is None, early return')
        return
    logger.debug(
        '_callback: isinstance Result=%s, result.data keys=%s, result==0=%s',
        isinstance(result, response.Result),
        result.data.keys() if hasattr(result.data, 'keys') else 'N/A',
        result == 0,
    )
    media = result.data.get('media')
    if media is None:
        logger.error("_callback: result.data.get('media') returned None, data=%s", result.data)
        return
    mark_compress_outcome(result)


def _compress(*args, ctx: Context, medias: list = [], **kwargs):
    scheduler = getattr(media_compress, 'core')
    tasks = [partial(scheduler, media) for media in medias]
    result = Folder.run___(*args, tasks=tasks, callback_list=[_callback], **kwargs)
    return result


# Scan to find un-compressed media. Then compress them.
compress = MiddlewareScheduler()
compress.add_middleware(_config)
compress.add_middleware(_scan)
compress.add_middleware(_query)
compress.add_func('core')(_compress)
compress.initialize()


# --- Trivial scheduler replacements (MiddlewareScheduler → _scheduler) ---
# These were MiddlewareScheduler instances wrapping one middleware + identity _core.
# Each middleware did the real work then called ctx.next() → identity returns result.
# Now they call the core logic directly and return the result.


def _run_folder_action(**kwargs):
    """Run a Folder action by extracting relevant kwargs."""
    action = kwargs.pop('action', '')
    folder_path = kwargs.pop('folder', '')
    kwargs.pop('cpu_limit', None)
    return Folder.run_(media_method=action, path=folder_path, **kwargs)


scale = _scheduler(
    lambda **kwargs: Folder.run_(
        media_method=kwargs.get('action', 'scale'),
        path=kwargs.get('folder', ''),
        **{k: v for k, v in kwargs.items() if k not in ('action', 'folder', 'cpu_limit')},
    )
)


change_file_extension = _scheduler(
    lambda **kwargs: file.change_file_extension(
        **{k: v for k, v in kwargs.items() if k in ('old_ext', 'ext', 'folder') and v}
    )
)


convert_format = _scheduler(lambda **kwargs: _run_folder_action(**kwargs))


save_text = _scheduler(
    lambda **kwargs: Folder.run_(
        media_method='save_text',
        path=kwargs.get('folder', ''),
        media_type=kwargs.get('type', 'video'),
        **{k: v for k, v in kwargs.items() if k not in ('action', 'folder', 'cpu_limit', 'type', 'worker')},
    )
)


def _video_action(name):
    """Build a _scheduler running a named Video method over the folder's videos."""
    return _scheduler(
        lambda **kwargs: Folder.run_(
            media_method=name,
            path=kwargs.get('folder', ''),
            media_type='video',
            max_workers=kwargs.get('max_workers', CONFIG.MAX_WORKERS),
        )
    )


combine = _video_action('combine')
reverse = _video_action('reverse')
decode = _video_action('decode')
delete_voice = _video_action('delete_voice')
save_metadata = _video_action('save_metadata')
set_metadata = _video_action('set_metadata')


images_to_video = _scheduler(
    lambda **kwargs: Folder.images_to_video(
        images_path=kwargs.get('images_path', ''),
        image_format=kwargs.get('image_format', 'jpg'),
        bit_rate=kwargs.get('bit_rate', '5000k'),
    )
)

concat = _scheduler(lambda **kwargs: Folder.concat(concat_list=kwargs.get('concat_list', '')))


def _stop(**kwargs):
    force = kwargs.get('force', False)
    pid_path = _Path.home() / '.mediakit' / 'daemon.pid'

    if not pid_path.exists():
        logger.info('No running daemon found.')
        return

    pid = int(pid_path.read_text().strip())

    try:
        _os.kill(pid, 0)
    except ProcessLookupError:
        logger.info('No running daemon found (stale PID file).')
        pid_path.unlink(missing_ok=True)
        return
    except PermissionError:
        logger.warning('Permission denied checking PID %d', pid)
        return

    if force:
        logger.info('Force-stopping daemon PID %d and all child processes...', pid)
        pgid = _os.getpgid(pid)
        _os.killpg(pgid, _signal.SIGKILL)
    else:
        logger.info('Stopping daemon PID %d gracefully...', pid)
        _os.kill(pid, _signal.SIGTERM)

    logger.info('Stop signal sent to PID %d.', pid)


from .watcher import WatcherScheduler  # noqa: E402

watch = WatcherScheduler()

stop = _scheduler(_stop)


from .dedupe import dedupe as _dedupe_func  # noqa: E402

dedupe = _scheduler(lambda **kwargs: _dedupe_func(**kwargs))


if __name__ == '__main__':
    result = getattr(compress, 'core')(folder=CONFIG.MEDIA_FILE_FOLDER, type='video', worker=1)
    logger.info(result)
