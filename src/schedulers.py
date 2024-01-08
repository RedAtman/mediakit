from concurrent.futures import Future
from functools import partial

from config import CONFIG
from folder import Folder
from logger import logger
from src.patterns.middleware_context_closure import Context, MiddlewareScheduler
from utils import response
from utils.executor import TaskManager

# from utils.colorprint import ColorPrint as logger


# Set media state before compress.
media_scheduler = MiddlewareScheduler()

@media_scheduler.add_middleware
def update_state(self, *args, ctx: Context, **kwargs):
    logger.json((self, args, kwargs))
    # logger.json(self.media.state)
    result = self.media.update_state('compress', 1)
    # logger.json(ctx.args, ctx.kwargs)
    # result = ctx.next(*args, **kwargs)
    # logger.json(result)
    assert isinstance(result, response.Result)
    if result == 200:
        # logger.json(self.media.state)
        return ctx.next(self, *args, **kwargs)
    else:
        raise Exception('Cannot update state.')

@media_scheduler.add_func('compress')
def core(self, *args, ctx: Context, **kwargs):
    logger.json((self, args, kwargs))
    result = self.quick_compress()
    logger.json(result)
    assert isinstance(result, response.Result)
    if result == 200:
        logger.json(ctx.next.__name__)
        # result = ctx.next(self, *args, **kwargs)
        # logger.debug(('compress core result', result))
        return result
    else:
        result = self.media.update_state('compress', 0)
        raise Exception('Cannot compress media.')

media_scheduler.initialize()


# Scan to find un-compressed media. Then compress them.
folder_scheduler = MiddlewareScheduler()

# scheduler.add_middleware(lambda ctx: setattr(ctx, 'result', Folder._scan()))

folder = Folder(CONFIG.MEDIA_FILE_FOLDER)
# folder = Folder('/Users/nut/Downloads/rs/_')

@folder_scheduler.add_middleware
def scan(*args, ctx: Context, **kwargs):
    logger.json((args, kwargs))
    result = folder.scan_media()
    # result = Folder.scan_media__()
    logger.json(result)
    # logger.json(ctx.args, ctx.kwargs)
    return ctx.next(*args, **kwargs)

@folder_scheduler.add_middleware
def query(*args, ctx: Context, **kwargs):
    logger.json((args, kwargs))
    QUERY_UN_COMPRESS = folder.get_query_statement('QUERY_UN_COMPRESS')
    result = folder.query(QUERY_UN_COMPRESS)
    logger.json(result)
    assert isinstance(result, response.Result)
    assert result == 200
    assert result == 'Success'
    medias = [folder.MEDIA_CLS(media.path) for media in result.data]
    logger.json(ctx.args, ctx.kwargs)
    # args = args + (result, )
    # kwargs.update({'medias': medias})
    return ctx.next(*args, medias=medias, **kwargs)

def callback(future: Future, *args, **kwargs):
    result = future.result()
    logger.json((result, args, kwargs))
    assert isinstance(result, response.Result)
    media = result.data.get('media')
    logger.debug((media, type(media)))
    if result == 200:
        media.update_state('compress', 2)
    else:
        media.update_state('compress', 0)

@folder_scheduler.add_func('compress')
def core(*args, ctx: Context, medias=[], **kwargs):
    logger.warning(('args, ctx: Context, **kwargs', args, ctx, kwargs))
    logger.json((args, ctx, kwargs))
    logger.json((ctx.next, ctx.args, ctx.kwargs))
    # result = Folder.run_(
    #     'quick_compress',
    #     *args,
    #     callback_list=[callback, ],
    #     **kwargs,
    # )
    scheduler = getattr(media_scheduler, 'compress')
    tasks = [partial(scheduler, media) for media in medias]
    result = Folder.run___(
        *args,
        tasks=tasks,
        callback_list=[callback, ],
        max_workers=1,
        **kwargs,
    )
    logger.info(('result', result))
    return result

# folder_scheduler.add_middleware(Folder._compress)
# folder_scheduler.add_func('compress')(lambda ctx: ctx.result)
# folder_scheduler.add_func('compress')(core)
# folder_scheduler.add_func('compress')(lambda: Folder._compress)

folder_scheduler.initialize()
# result = folder_scheduler.compress()
# result = getattr(folder_scheduler, 'compress')()
# logger.debug(result)
