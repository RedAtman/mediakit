import logging

from base.video import Video
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from utils import response


logger = logging.getLogger()


# Set media state before compress.
compress = MiddlewareScheduler()


@compress.add_middleware
def update_state(self: Video, *args, ctx: Context, **kwargs):
    logger.info((self, args, kwargs))
    # logger.info(self.media.state)
    result = self.media.update_state("compress", 1)
    # logger.info(ctx.args, ctx.kwargs)
    # result = ctx.next(*args, **kwargs)
    # logger.info(result)
    logger.info(ctx.next.__name__)
    assert isinstance(result, response.Result)
    if result == 200:
        # logger.info(self.media.state)
        return ctx.next(self, *args, **kwargs)
    else:
        raise Exception("Cannot update state.")


@compress.add_func("core")
def _compress(self: Video, *args, ctx: Context, **kwargs):
    logger.info((self, args, kwargs))
    result = self.quick_compress()
    logger.warning("-" * 80)
    logger.info(result)
    assert isinstance(result, response.Result)
    if result == 200:
        # result = ctx.next(self, *args, **kwargs)
        # logger.debug(('compress core result', result))
        return result
    else:
        result = self.media.update_state("compress", 0)
        raise Exception("Cannot compress media.")


compress.initialize()
