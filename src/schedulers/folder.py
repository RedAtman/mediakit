from concurrent.futures import Future
from functools import partial
import logging
from typing import Any

from config import CONFIG
from folder import Folder
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from src.schemas import StateChoices
from utils import file, response
from utils.command import CommandExecutor
from utils.throttle import CPULimiterCoordinator

from .media import compress as media_compress


# Global CPU throttling coordinator
_coordinator = CPULimiterCoordinator(
    default_limit=CONFIG.CPU_LIMIT,
    auto_mode=True,
)
CommandExecutor.coordinator = _coordinator


__all__ = [
    "compress",
    "scale",
    "change_file_extension",
    "convert_format",
    "save_text",
]


logger = logging.getLogger()


class _SimpleScheduler:
    """Wrapper giving a plain function a .core attribute for CLI dispatch."""
    def __init__(self, func):
        self.core = func


def _config(*args: Any, ctx: Context, **kwargs: dict[str, Any]):
    cpu_limit = kwargs.pop('cpu_limit', None)
    if isinstance(cpu_limit, str) and cpu_limit.isdigit():
        cpu_limit = int(cpu_limit)
    if isinstance(cpu_limit, int) and cpu_limit > 0:
        _coordinator.set_manual_override(cpu_limit)
    logger.debug(CONFIG.CPU_LIMIT)
    return ctx.next(*args, **kwargs)


def _scan(*args: Any, ctx: Context, **kwargs: dict[str, Any]):
    _folder = kwargs.get("folder", CONFIG.MEDIA_FILE_FOLDER)
    assert isinstance(_folder, str), "Expected a string for path, but got %s" % type(_folder).__name__
    try:
        folder = Folder(_folder)
    except FileNotFoundError as exc:
        return
    folder.scan_media()
    kwargs["folder"] = folder
    return ctx.next(*args, **kwargs)


def _query(*args: Any, ctx: Context, folder: Folder, **kwargs: dict[str, Any]):
    QUERY_UNPROCESSED = folder.get_query_statement("QUERY_UNPROCESSED")
    if not isinstance(QUERY_UNPROCESSED, folder.VALID_QUERY_TYPE):
        raise ValueError("Invalid query statement")
    result = folder.query(QUERY_UNPROCESSED)
    assert isinstance(result, response.Result)
    assert result == 0
    assert result == "Success"
    medias = [folder.MEDIA_CLS(media.path) for media in result.data]
    if not medias:
        pass
    return ctx.next(*args, medias=medias, **kwargs)


def _callback(future: Future, *args, **kwargs):
    logger.debug("_callback entered, args=%s, kwargs=%s", args, kwargs)
    try:
        result = future.result()
        logger.debug("_callback: future.result() type=%s, data=%s, result=%s",
                     type(result).__name__,
                     result.data if hasattr(result, 'data') else 'N/A',
                     result)
    except Exception as exc:
        logger.error("_callback: future.result() raised %s: %s", type(exc).__name__, exc)
        return
    if result.data is None:
        logger.debug("_callback: result.data is None, early return")
        return
    logger.debug("_callback: isinstance Result=%s, result.data keys=%s, result==0=%s",
                 isinstance(result, response.Result),
                 result.data.keys() if hasattr(result.data, 'keys') else 'N/A',
                 result == 0)
    media = result.data.get("media")
    if media is None:
        logger.error("_callback: result.data.get('media') returned None, data=%s", result.data)
        return
    if result == 0:
        logger.debug("_callback: SUCCESS path, setting state to finished=2, media.model=%s", media.model)
        try:
            update_result = media.model.update_state("compress", StateChoices.finished)
            logger.debug("_callback: update_state(finished) returned %s", update_result)
        except Exception as exc:
            logger.error("_callback: update_state(finished) raised %s: %s", type(exc).__name__, exc)
        try:
            file.soft_remove(media.path)
            logger.debug("_callback: soft_remove completed for %s", media.path)
        except Exception as exc:
            logger.error("_callback: soft_remove(%s) raised %s: %s", media.path, type(exc).__name__, exc)
    else:
        logger.debug("_callback: FAILURE path (result=%s), setting state to failed=-2", result)
        try:
            update_result = media.model.update_state("compress", StateChoices.failed)
            logger.debug("_callback: update_state(failed) returned %s", update_result)
        except Exception as exc:
            logger.error("_callback: update_state(failed) raised %s: %s", type(exc).__name__, exc)


def _compress(*args, ctx: Context, medias: list = [], **kwargs):
    scheduler = getattr(media_compress, "core")
    tasks = [partial(scheduler, media) for media in medias]
    result = Folder.run___(
        *args,
        tasks=tasks,
        callback_list=[
            _callback,
        ],
        **kwargs,
    )
    return result


# Scan to find un-compressed media. Then compress them.
compress = MiddlewareScheduler()
compress.add_middleware(_config)
compress.add_middleware(_scan)
compress.add_middleware(_query)
compress.add_func("core")(_compress)
compress.initialize()


# --- Trivial scheduler replacements (MiddlewareScheduler → _SimpleScheduler) ---
# These were MiddlewareScheduler instances wrapping one middleware + identity _core.
# Each middleware did the real work then called ctx.next() → identity returns result.
# Now they call the core logic directly and return the result.


def _run_folder_action(**kwargs):
    """Run a Folder action by extracting relevant kwargs."""
    action = kwargs.pop('action', '')
    folder_path = kwargs.pop('folder', '')
    kwargs.pop('cpu_limit', None)
    return Folder.run_(
        media_method=action,
        path=folder_path,
        **kwargs,
    )


scale = _SimpleScheduler(
    lambda **kwargs: Folder.run_(
        media_method=kwargs.get('action', 'scale'),
        path=kwargs.get('folder', ''),
        **{k: v for k, v in kwargs.items() if k not in ('action', 'folder', 'cpu_limit')},
    )
)


change_file_extension = _SimpleScheduler(
    lambda **kwargs: file.change_file_extension(
        **{k: v for k, v in kwargs.items() if k in ('old_ext', 'ext', 'folder') and v},
    )
)


convert_format = _SimpleScheduler(
    lambda **kwargs: _run_folder_action(**kwargs)
)


save_text = _SimpleScheduler(
    lambda **kwargs: Folder.run_(
        media_method='save_text',
        path=kwargs.get('folder', ''),
        media_type=kwargs.get('type', 'video'),
        **{k: v for k, v in kwargs.items() if k not in ('action', 'folder', 'cpu_limit', 'type', 'worker')},
    )
)



if __name__ == "__main__":
    result = getattr(compress, "core")(folder=CONFIG.MEDIA_FILE_FOLDER, type="video", worker=1)
    logger.info(result)
