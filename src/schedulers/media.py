import logging

from base.video import Video
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from utils import response


__all__ = ["compress"]

logger = logging.getLogger()


compress = MiddlewareScheduler()


@compress.add_middleware
def update_state(self: Video, *args, ctx: Context, **kwargs):
    result = self.media.update_state("compress", 1)
    assert isinstance(result, response.Result)
    if result == 200:
        return ctx.next(self, *args, **kwargs)
    else:
        raise Exception("Cannot update state.")


@compress.add_func("core")
def _compress(self: Video, *args, ctx: Context, **kwargs):
    result = self.quick_compress()
    assert isinstance(result, response.Result)
    if result == 200:
        return result
    else:
        result = self.media.update_state("compress", 0)
        raise Exception("Cannot compress media.")


compress.initialize()
