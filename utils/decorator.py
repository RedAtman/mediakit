import functools
import time
import subprocess
from utils import log


def timekeep(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        start_time = time.time()
        ret = func(*args, **kwargs)
        log.warning(
            '<TASK>%s,耗时:%s' % (func.__name__, time.time() - start_time),
            # '执行结果:', ret,
            )
        return ret
    return inner


def Timekeep():
    """
    用于类方法(可调用self)的装饰器
    """
    def wrapper(func):
        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            start_time = time.time()
            log.debug('Task start(%s):' % (func.__name__), start_time)
            ret = func(self, *args, **kwargs)
            log.warning(
                '<TASK>%s,耗时:%s' % (func.__name__, time.time() - start_time)
                # '执行结果:', ret
                )
            return ret
        return inner
    return wrapper


def Executor():
    '''执行shell命令（用于类方法的可调用self的装饰器）
    '''
    def wrapper(func):
        @functools.wraps(func)
        def inner(self, *args, **kwargs):
            ret = func(self, *args, **kwargs)
            # start_time = time.time()
            # log.info('Task(%s) start at %s' % (func.__name__,start_time), self.order)
            # ret = os.popen('ping www.baidu.com')
            # ret = subprocess.Popen(self.order)
            # ret = subprocess.run(self.order)
            # ret = subprocess.Popen(
            # self.order, shell=False, stdout=subprocess.PIPE).stdout
            # self.order = ['ffmpeg', '-y', '-loglevel', 'info', '-i', '/Users/nut/Downloads/RS/test.mp4', '-s', '640x360', '-aspect', '640:360', '-threads', '0', '-c:v', 'hevc_videotoolbox', '-r', '24.00', '-pix_fmt', 'yuv420p', '-b:v', '800k', '-maxrate', '1000k', '-bufsize', '4M', '-allow_sw', '1', '-profile:v', 'main', '-vtag', 'hvc1', '-c:a:0', 'aac', '-ac:a:0', '2', '-ar:a:0', '32000', '-b:a:0', '128k', '-strict', '-2', '-sn', '-f', 'mp4', '-map', '0:0', '-map', '0:1', '-map_chapters', '0', '-max_muxing_queue_size', '40000', '-map_metadata', '0', '/Users/nut/Downloads/RS/_compress/test-compress_6.mp4']
            p = subprocess.Popen(self.order, shell=False, stdout=subprocess.PIPE)
            # log.info('Executor ret',type(ret),ret.stdout.read(),ret.returncode,ret.stdout,ret.terminate(),ret.wait())
            log.debug('Executor waiting...',self.order)
            result = {
                'returncode': p.wait(),
                'result': p.communicate()[0],
                }
            # for i in iter(p.stdout.readlines,'b'):
            #     time.sleep(1)
            #     print('-'*20,
            #         # p.poll(),
            #         # p.returncode
            #         )
            #     print(i)
            # ret = ret
            # duration = time.time() - start_time
            log.debug('Executor finish!',result)
            return dict(ret,**result) if type(ret) == dict else result
        return inner
    return wrapper


def executor(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        order = func(*args, **kwargs)
        p = subprocess.Popen(order, shell=False, stdout=subprocess.PIPE)
        log.debug('Executor waiting...',order)
        result = {
            'returncode': p.wait(),
            'result': p.communicate()[0],
            }
        log.debug('Executor finish!', order, result)
        return dict(order,**result) if type(order) == dict else result
    return inner