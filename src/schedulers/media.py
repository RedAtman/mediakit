import logging
import os
import shutil
from typing import Dict

from base.video import Video
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from utils import response


__all__ = ["compress"]

logger = logging.getLogger()


def update_state(self: Video, *args, ctx: Context, key="compress", val=1, **kwargs):
    result = self.media.update_state(key, val)
    assert isinstance(result, response.Result)
    assert result == 200
    return ctx.next(self, *args, **kwargs)


def soft_remove(self: Video, *args, ctx: Context, **kwargs):
    remove_folder = os.path.join(self.dirname, ".removed")
    if not os.path.exists(remove_folder):
        os.makedirs(remove_folder)
    shutil.move(self.path, os.path.join(remove_folder, self.title + "." + self.ext))
    return ctx.next(*args, **kwargs)


def _compress(
    self: Video, *args, ctx: Context, action: str = "compress", **kwargs: Dict[str, str]
):
    result = getattr(self, action)()
    assert isinstance(result, response.Result)
    assert result == 200
    return ctx.next(self, *args, val=2, result=result, **kwargs)


compress = MiddlewareScheduler()
compress.add_middleware(update_state)
compress.add_middleware(_compress)
compress.add_middleware(update_state)
compress.add_middleware(soft_remove)
compress.add_func("core")(lambda *args, ctx, result, **kwargs: result)
compress.initialize()
