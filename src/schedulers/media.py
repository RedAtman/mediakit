import logging
from typing import Dict

from base.video import Video
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from utils import decorator, response


__all__ = ["compress"]

logger = logging.getLogger()


def update_state(self: Video, *args, ctx: Context, key="compress", val=1, **kwargs):
    result = self.media.update_state(key, val)
    assert isinstance(result, response.Result)
    assert result == 0
    return ctx.next(self, *args, **kwargs)


def _compress(
    self: Video, *args, ctx: Context, action: str = "compress", **kwargs: Dict[str, str]
):
    result = decorator.exception(getattr(self, action))()
    return ctx.next(self, *args, result=result, **kwargs)


compress = MiddlewareScheduler()
compress.add_middleware(update_state)
compress.add_middleware(_compress)
compress.add_func("core")(lambda *args, ctx, result, **kwargs: result)
compress.initialize()
