from concurrent.futures import Future
from functools import partial
import logging
from typing import Any, Dict

from config import CONFIG
from folder import Folder
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from utils import response

from .media import compress as media_compress


__all__ = ["compress", "change_file_extension", "convert_format"]

logger = logging.getLogger()


def _core(*args, ctx: Context, result=None, **kwargs):
    return result


# scheduler.add_middleware(lambda ctx: setattr(ctx, 'result', Folder._scan()))


def scan(*args, ctx: Context, **kwargs):
    folder = Folder(kwargs.get("folder", CONFIG.MEDIA_FILE_FOLDER))
    result = folder.scan_media()
    # result = Folder.scan_media__()
    return ctx.next(*args, **kwargs)


def query(*args, ctx: Context, **kwargs):
    folder = Folder(kwargs.get("folder", CONFIG.MEDIA_FILE_FOLDER))
    QUERY_UN_COMPRESS = folder.get_query_statement("QUERY_UN_COMPRESS")
    result = folder.query(QUERY_UN_COMPRESS)
    assert isinstance(result, response.Result)
    assert result == 0
    assert result == "Success"
    medias = [folder.MEDIA_CLS(media.path) for media in result.data]
    return ctx.next(*args, medias=medias, **kwargs)


def callback(future: Future, *args, **kwargs):
    result = future.result()
    assert isinstance(result, response.Result)
    media = result.data.get("media")
    if result == 200:
        media.update_state("compress", 2)
    else:
        media.update_state("compress", 0)


def _compress(*args, ctx: Context, medias=[], **kwargs):
    # result = Folder.run_(
    #     'compress',
    #     *args,
    #     callback_list=[callback, ],
    #     **kwargs,
    # )
    scheduler = getattr(media_compress, "core")
    tasks = [partial(scheduler, media) for media in medias]
    result = Folder.run___(
        *args,
        tasks=tasks,
        callback_list=[
            # callback,
        ],
        max_workers=1,
        **kwargs,
    )
    return result


# compress.add_middleware(Folder._compress)
# compress.add_func('compress')(lambda ctx: ctx.result)
# compress.add_func('compress')(core)
# compress.add_func('compress')(lambda: Folder._compress)

# Scan to find un-compressed media. Then compress them.
compress = MiddlewareScheduler()
compress.add_middleware(scan)
compress.add_middleware(query)
compress.add_func("core")(_compress)
compress.initialize()


def _change_file_extension(*args, ctx: Context, **kwargs):
    from utils import folder

    result = folder.change_file_extension(*ctx.args, **ctx.kwargs)
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
    ext: str = "",
    **kwargs: Dict[str, Any],
):
    result = Folder.run_(
        media_method=action,
        path=folder,
        ext=ext,
    )
    assert isinstance(result, list)
    return ctx.next(*args, result=result, **kwargs)


convert_format = MiddlewareScheduler()
convert_format.add_middleware(_convert_format)
convert_format.add_func("core")(_core)
convert_format.initialize()


def _save_text(
    *args, ctx: Context, action: str = "convert_format", folder: str = "", **kwargs
):
    result = Folder.run_(
        *args,
        media_method="save_text",
        path=folder,
        **kwargs,
    )
    return ctx.next(*args, result=result, **kwargs)


save_text = MiddlewareScheduler()
save_text.add_middleware(_save_text)
save_text.add_func("core")(_core)
save_text.initialize()

if __name__ == "__main__":
    result = getattr(compress, "core")(
        folder=CONFIG.MEDIA_FILE_FOLDER, type="video", worker=1
    )
    logger.info(result)
