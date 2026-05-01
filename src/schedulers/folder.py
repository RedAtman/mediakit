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


def _core(*args, ctx: Context, result=None, **kwargs):
    return result


def _config(*args: Any, ctx: Context, **kwargs: dict[str, Any]):
    cpu_limit = kwargs.pop('cpu_limit')
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
        # logger.warning("Folder not found: %s", _folder)
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
        # logger.info("No media to compress: %s", folder.path)
    return ctx.next(*args, medias=medias, **kwargs)


def _callback(future: Future, *args, **kwargs):
    result = future.result()
    if result.data is None:
        logger.warning(f"No media to compress: {args}, {kwargs}")
        return
    assert isinstance(result, response.Result)
    media = result.data.get("media")
    if result == 0:
        media.model.update_state("compress", StateChoices.finished)
        file.soft_remove(media.path)
    else:
        media.model.update_state("compress", StateChoices.failed)


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


# scheduler.add_middleware(lambda ctx: setattr(ctx, 'result', Folder._scan()))

# Scan to find un-compressed media. Then compress them.
compress = MiddlewareScheduler()
compress.add_middleware(_config)
compress.add_middleware(_scan)
compress.add_middleware(_query)
compress.add_func("core")(_compress)
compress.initialize()


def _scale(
    *args,
    ctx: Context,
    action: str = "scale",
    folder: str = "",
    **kwargs,
):
    result = Folder.run_(
        *args,
        media_method=action,
        path=folder,
        **kwargs,
    )
    return ctx.next(*args, result=result, **kwargs)


scale = MiddlewareScheduler()
scale.add_middleware(_scale)
scale.add_func("core")(_core)
scale.initialize()


def _change_file_extension(*args, ctx: Context, **kwargs):
    result = file.change_file_extension(*ctx.args, **ctx.kwargs)
    return ctx.next(*args, result=result, **kwargs)


change_file_extension = MiddlewareScheduler()
change_file_extension.add_middleware(_change_file_extension)
change_file_extension.add_func("core")(_core)
change_file_extension.initialize()


def _convert_format(
    *args,
    ctx: Context,
    action: str = "convert_format",
    folder: str = "",
    **kwargs: dict[str, Any],
):
    result = Folder.run_(
        media_method=action,
        path=folder,
        **kwargs,
    )
    assert isinstance(result, list)
    return ctx.next(*args, result=result, **kwargs)


convert_format = MiddlewareScheduler()
convert_format.add_middleware(_convert_format)
convert_format.add_func("core")(_core)
convert_format.initialize()


def _save_text(*args, ctx: Context, action: str = "convert_format", folder: str = "", type: str = "video", **kwargs):
    result = Folder.run_(
        *args,
        media_method="save_text",
        media_type=type,
        path=folder,
        **kwargs,
    )
    return ctx.next(*args, result=result, **kwargs)


save_text = MiddlewareScheduler()
save_text.add_middleware(_save_text)
save_text.add_func("core")(_core)
save_text.initialize()


if __name__ == "__main__":
    result = getattr(compress, "core")(folder=CONFIG.MEDIA_FILE_FOLDER, type="video", worker=1)
    logger.info(result)
