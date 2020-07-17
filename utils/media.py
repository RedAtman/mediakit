import re,json
import time
import subprocess
import copy
import functools
import os,sys
from concurrent import futures
import threading
import queue

from utils import log,translate,decorator,BoundedExecutor

lock = threading.Lock()

class Audio(object):
    '''docstring for Audio'''

    def __init__(self, cls):
        # self.arg = arg
        print('cls', type(cls), cls)


class Media(object):
    '''docstring for Media'''
    __order_prefix = ['ffmpeg', '-y', '-loglevel', 'info']
    # __thread_pool = futures.ThreadPoolExecutor(max_workers=64)
    # __queue = queue.Queue(maxsize=0)
    __lock = threading.Lock()

    def __init__(self, file_path, title=None, artist=None, category=None, camera=None, lens=None, keywords=None,loglevel='info'):
        '''
        :params
            file_path(String): 媒体文件路径。
            title: string, 视频标题;
            artist(list): 视频作者;
            keywords: dict{key:list} / list, 视频关键词;
        '''
        self.file_path = file_path.strip()
        self.dir, self.title, self.format = self.get_file_info(self.file_path)
        # self.audio = {
        #     "path": {"input": ""}
        # }
        self.artist = artist
        self.album_artist = artist
        self.category = category
        self.camera = camera
        self.lens = lens
        self.keywords = keywords
        self.keywords_list = set()
        self.order_prefix = ['ffmpeg', '-y', '-loglevel', loglevel]
        # self.lock = threading.Lock()

    @property
    def metadata(self):
        return self.get_metadata(self.file_path)

    @property
    def duration(self):
        '''媒体时长（单位/s）
        '''
        # result = subprocess.run([
        #     "ffprobe", "-v", "error", "-show_entries",
        #     "format=duration", "-of",
        #     "default=noprint_wrappers=1:nokey=1", self.path],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.STDOUT)
        # return float(result.stdout)

        return self.metadata.get('streams')[0].get('duration')

    @property
    def output_path(self):
        '''媒体输出路径
        '''
        time_str = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        # path = self.dir + "/_" + self.title + "_" + \
        #     str(int(round(time.time() * 1000))) + "." + self.format
        path = self.dir + "/_" + self.title + "_" + \
            time_str + "." + self.format
        log.debug('output path', path)
        return path

    @staticmethod
    def get_file_info(file_path):
        '''获取媒体文件三个数据: file_dir, file_title, file_format。
        :param: file_path(str): 媒体文件路径。
        '''
        return re.findall(
            '(.*)\/([^<>/\\\|:""\?]+)\.(\w+)$', file_path)[0]

    @staticmethod
    def get_metadata(file_path):
        '''获取媒体元数据。
        :param: file_path(str): 媒体文件路径。
        '''
        file_path = file_path.strip()
        @decorator.Timekeep()
        @decorator.executor
        def func(file_path):
            return ['ffprobe', '-v', 'quiet', '-show_format',
                          '-show_streams', '-print_format', 'json', file_path]

        result = func(file_path)
        if result.get('returncode') == 0:
            ret = json.loads(result.get('result'))
        else:
            raise TypeError('%s is not JSONable' % type(result))
        log.debug('get_metadata func', ret)
        return ret

    @classmethod
    def create_file_path(cls, file_path, suffix='suffix', suffix_number=1, lock=None):
        '''产生媒体剪切片段输出路径
        :param: suffix_number(number): 1
        :reture: str:/Users/nut/Downloads/RS/_trim/HNK91_trim_1.mp4
        '''

        file_dir, file_title, file_format = cls.get_file_info(file_path)
        file_dir = os.path.join(file_dir, '_' + suffix)
        if not os.path.exists(file_dir):
            try:
                os.mkdir(file_dir)
            except Exception as e:
                try:
                    os.makedirs(file_dir)
                except Exception as e:
                    # print('mkdirs', e)
                    # os.makedirs(self.save_dir)
                    pass

        if lock:
            lock.acquire()
        try:
            suffix_number = suffix_number or 1
            file_path = os.path.join(file_dir, file_title + "-" + suffix + '_' + \
                    str(suffix_number) + "." + file_format)
            while os.path.exists(file_path):
                suffix_number += 1
                file_path = os.path.join(file_dir, file_title + "-" + suffix + '_' + \
                    str(suffix_number) + "." + file_format)
            log.warning('file_path',file_path)
            open(file_path, encoding='utf-8', mode='x')
        except Exception as e:
            raise
        else:
            pass
        finally:
            if lock:
                lock.release()
        log.info('create_file_path',file_path)
        return file_path

    @property
    def order_metadata(self):
        '''生成获取视频元数据的命令行执行order(List); 同时生成 keywords_list;
        '''
        meta_key_list = ['title', 'artist', 'album_artist',
                         'category', 'camera', 'lens', 'keywords']
        order_metadata = []
        for key in meta_key_list:
            meta = getattr(self, key)
            if not meta:
                continue
            # print('order_metadata', key, meta)
            if isinstance(meta, str):
                order_metadata.extend(['-metadata', str(key) + '=' + meta])
                self.keywords_list.add(meta)
            if isinstance(meta, list):
                order_metadata.extend(
                    ['-metadata', str(key) + '=' + ",".join(meta)])
                # log.info('meta', type(meta), meta)
                self.keywords_list.update(meta)
            # 若是dict 则拼接values
            if isinstance(meta, dict):
                from functools import reduce

                def concat(a, b):
                    log.info('concat', type(a), type(b))
                    a.extend(b)
                    return a

                meta_concat = reduce(concat, list(meta.values()))
                log.info('meta_concat', meta_concat)

                order_metadata.extend(
                    ['-metadata', str(key) + '=' + ",".join(meta_concat)])
                self.keywords_list.update(meta_concat)
        # print('order_metadata,self.keywords_list', order_metadata,self.keywords_list)

        # print('translate',translate.translate,dir(translate.translate))
        keywords_en_list = translate.translate.result(self.keywords_list)
        self.keywords_list.update(keywords_en_list)
        self.keywords_list = {i.strip() for i in self.keywords_list}
        log.info('keywords_list', self.keywords_list)
        order_metadata.extend(
            ['-metadata', 'keywords' + '=' + ",".join(self.keywords_list)])
        log.info('order_metadata', order_metadata)

        return order_metadata


    @decorator.Timekeep()
    @decorator.Executor()
    def save_metadata(self):
        '''读取现有文件的元数据 并保存为txt文件
        '''
        self.order = copy.deepcopy(self.order_prefix)
        metadata_path = self.dir + "/" + self.title + '_metadate' + ".txt"
        self.order.extend(['-i', self.path,
                           '-f', 'ffmetadata', metadata_path])

    @decorator.Timekeep()
    @decorator.Executor()
    def set_metadata(self):
        '''设置元数据
        '''
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend(['-i', self.path])
        self.order.extend(self.order_metadata)
        self.order.extend(['-c:a', 'copy',
                           '-c:v', 'copy',
                           self.output_path])

    @decorator.Timekeep()
    @decorator.Executor()
    def add_voice(self, audio_path, audio_defer, fade_duration=1):
        '''添加声音 同时设置淡入淡出 及过度时长
        :param: audio_path(str): 声音文件路径
        :param: audio_defer(number): 声音文件截取处（单位/秒）
        :param: fade_duration(number): 淡入淡出过度时长（单位/秒，默认值：1）
        '''
        fade_order = "[1:a]afade=t=in:st=0:d=" + str(fade_duration) \
            + ",afade=t=out:st=" + str(self.duration - 1) \
            + ":d=" + str(fade_duration)
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend(['-i', self.path,
                           '-ss', audio_defer,
                           '-i', audio_path,
                           # '-vf',
                           # '[1:a]afade=in:0:5',
                           # 'afade=out:20:5',
                           # 'afade=t=in:ss=0:d=15',

                           # 设置淡入、淡出、及过度时长
                           '-filter_complex',
                           fade_order,

                           # 对video类型文件直接copy 不重新编码
                           '-c:v', 'copy',
                           # '-c', 'copy',

                           # 时长取最短的media
                           '-shortest',
                           self.output_path])

    @decorator.Timekeep()
    @decorator.Executor()
    def images_to_video(self, images_path, image_format, bit_rate='5000k'):
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend([
            # 关闭每帧都提醒是否overwrite
            '-pattern_type', 'glob',

            # 设置帧率
            '-r', '24',

            # 设置images文件路径,
            '-i', images_path + '/*.' + image_format,

            # 码率
            # '-b:v', bit_rate,

            # 线程(待验证)
            '-threads', '4',

            # 画面缩放比率
            '-vf', 'scale=1920:-1',

            # 对video类型文件设置编码类型
            # '-c:v', 'libx264',
            # '-c:v', 'libx265',

            # 时长取最短的media
            # '-shortest',
            images_path + '/output_' + bit_rate + '1920' + time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime()) + '.mp4'])

    @decorator.Timekeep()
    @decorator.Executor()
    def delete_voice(self):
        '''去除声音（静音）
        '''
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend(['-i', self.path])
        # order.extend(self.metadata)
        self.order.extend(['-an',
                           '-c:v', 'copy',
                           self.output_path])

    # @decorator.Timekeep()
    @decorator.Executor()
    def trim(self, time=(), suffix_number=1, lock=None):
        '''截取视频指定某一段时间
        :param: times(tuple): ("00:26:56", "00:28:36")
        :param: suffix_number(number): 1
        '''
        if not time:
            return False
        file_path = self.create_file_path(self.file_path, suffix='trim', suffix_number=suffix_number, lock=lock)
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend([

            # 截取时间
            '-ss', time[0],
            '-to', time[1],

            # 使用copy后 避免太过于精确切割而丢失帧
            '-accurate_seek',

            '-i', self.file_path,

            # 线程(待验证)
            '-threads', '4',

            # 对video类型文件设置编码类型
            # 注意：copy会带来前面一段时间丢帧问题并且无预览图
            # '-c', 'copy',
            # '-c:a', 'copy',
            # '-c:v', 'copy',

            # 若voice copy失败
            '-c:v', 'copy',
            '-acodec', 'aac',

            # '-avoid_negative_ts', '1',
            file_path])
        return {'path': file_path}

    def trim_mul(self, times=()):
        '''批量截取
        :param: times(tuple): ("00:26:56", "00:28:36")
        '''
        if not time:
            return False
        for time in times:
            # self.trim(ss=time[0], to=time[1])
            self.trim(time)

    @classmethod
    @decorator.Timekeep()
    def trim_mul_file(cls, files=[]):
        '''多线程批量文件截取
        :param: files(list):
            [
                {
                    'path':'/Users/nut/Downloads/RS/CCAV.mp4',
                    'trim_times':(
                        ("00:50:22", "01:03:27"),
                        ("01:19:39", "01:37:04")...
                    )
                }...
            ]
        '''
        executor = BoundedExecutor(20, 20)

        for file in files:
            suffix_number = 0
            for time in file.get('trim_times'):
                suffix_number += 1
                log.warning('suffix_number', suffix_number)
                # future = executor.submit(cls(file.get('path')).create_file_path, lock=executor.lock, suffix='trim', suffix_number=suffix_number)
                future = executor.submit(cls(file.get('path')).trim, time=time, suffix_number=suffix_number, lock=executor.lock)
                future.add_done_callback(cls.compress)
                log.info('trim_mul_file', time,suffix_number)
            executor.shutdown(wait=True)

        # cls.__thread_pool.shutdown(wait=True)
        log.warning('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe().f_code.co_name, threading.current_thread().getName(), os.getpid()))

    def test(self,future):
        log.warning('test self', self, future)
        pass

    @classmethod
    def thread_pool_excutor(cls, *args, callback=None, **kwargs):
        # with cls.__thread_pool as tp:
        #     task = tp.submit(
        #         *args,**kwargs)
        #     # task.add_done_callback(callback)

        #     cls.__thread_pool.shutdown(wait=True)
        #     log.info('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe().f_code.co_name,threading.current_thread().getName(), os.getpid()))

        task = cls.__thread_pool.submit(
            *args,**kwargs)
        # task.add_done_callback(callback)
        # cls.__queue.put(task)


        cls.__thread_pool.shutdown(wait=True)

        # result = futures.wait(cls.__queue, return_when=futures.ALL_COMPLETED)
        log.info('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe().f_code.co_name,threading.current_thread().getName(), os.getpid()))

    @classmethod
    def compress(cls, future, file_path=None, bit_rate=800):
        '''文件体积压缩
        :param: future(Object future): future.result()返回一个dict，其中path键对应待压缩文件路径。
        :param: file_path(number): 压缩比特率，默认800，单位k。
        :param: bit_rate(number): 压缩比特率，默认800，单位k。
        '''
        file_path = file_path or future.result().get('path')
        file_path = file_path.strip()

        file_dir, file_title, file_format = cls.get_file_info(file_path)
        compress_file_path = cls.create_file_path(file_path, suffix='compress', lock=None)

        @decorator.timekeep
        @decorator.executor
        def func():
            metadata = cls.get_metadata(file_path)
            if bit_rate > 800:
                pass
            else:
                width = 640
                rate = int(width / metadata.get('streams')[0].get('width'))
                height = int(rate * metadata.get('streams')[0].get('height'))
            log.info('compress width height',rate,metadata.get('streams')[0].get('width'),metadata.get('streams')[0].get('height'),width,height)

            order = copy.deepcopy(cls.__order_prefix)
            order.extend([
                '-i', file_path, 
                '-s', str(width)+'x'+str(height),
                '-aspect', str(width)+':'+str(height),
                '-threads', '0',
                '-c:v', 'hevc_videotoolbox',
                '-r', '24.00',
                '-pix_fmt', 'yuv420p',
                '-b:v', str(bit_rate) + 'k',
                '-maxrate', str(bit_rate + 200) + 'k',
                '-bufsize', '4M',
                '-allow_sw', '1',
                '-profile:v', 'main',
                '-vtag', 'hvc1',
                '-c:a:0', 'aac',
                '-ac:a:0', '2',
                '-ar:a:0', '32000',
                '-b:a:0', '128k',
                '-strict',
                '-2',
                '-sn',
                '-f', file_format,
                '-map', '0:0',
                '-map', '0:1',
                '-map_chapters', '0',
                '-max_muxing_queue_size', '40000',
                '-map_metadata', '0',
                compress_file_path])
            return order

        ret = func()
        return compress_file_path

    def transcode(self):
        log.info('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe().f_code.co_name,threading.current_thread().getName(), os.getpid()))
        pass

    def decode(self, format='mov'):
        '''
        '''
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend([
            '-i', self.file_path,

            # 线程(待验证)
            # '-threads', '4',

            # '-avoid_negative_ts', '1',
            self.dir + "/" + self.title + "_decode_." + format])

    def concat(self):

        return 'ffmpeg -f concat -i concat.txt -c copy concat.mov'
