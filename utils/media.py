import re
import json
import time
import subprocess
import copy
import functools
import os
import sys
from concurrent import futures
import threading
import queue

from utils import log, translate, decorator, BoundedExecutor

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

    def __init__(self, file_path, title=None, artist=None, category=None, camera=None, lens=None, keywords=None, loglevel='info'):
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
        self.order_prefix_v2 = ['ffmpeg', '-y', '-loglevel',
                                loglevel, '-i', self.file_path, ]
        # self.lock = threading.Lock()

    @property
    def metadata(self):
        result = self.get_metadata(self.file_path)
        log.warning('线程:%s, 父进程:%s, <Task (%s) start...>, %s' % (threading.current_thread(
        ).getName(), os.getpid(), sys._getframe().f_code.co_name, result))
        return result

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
        return self.get_output_path('')

    def get_output_path(self, suffix=''):
        '''媒体输出路径(代替 self.output_path)
        '''
        caller = sys._getframe().f_back.f_code.co_name
        suffix = suffix or caller
        suffix = suffix + '_' + time.strftime("%Y%m%d%H%M%S", time.localtime())

        path = self.dir + "/_" + self.title + "_" + \
            suffix + "." + self.format
        log.debug('output path', path)
        return path

    @staticmethod
    def get_file_info(file_path):
        '''获取媒体文件三个数据: file_dir, file_title, file_format。
        :param: file_path(str): 媒体文件路径。
        '''
        return re.findall(
            '(.*)\/([^<>/\\\|:""\?]+)\.(\w+)$', file_path)[0]
        # return os.path.

    @staticmethod
    def get_metadata(file_path):
        '''获取媒体元数据。
        :param: file_path(str): 媒体文件路径。
        '''
        file_path = file_path.strip()
        # @decorator.Timekeep()

        @decorator.executor
        # @decorator.Executor()
        def get_metadata(file_path):
            return ['ffprobe', '-v', 'quiet', '-show_format',
                    '-show_streams', '-print_format', 'json', file_path]

        result = get_metadata(file_path)
        log.info('get_metadata result', result.get('result'))
        if result.get('returncode') == 0:
            metadata = json.loads(result.get('result'))
        else:
            raise TypeError('%s is not JSONable' % type(result))
        return metadata

    @classmethod
    def get_width(cls, file_path):
        metadata = cls.get_metadata(file_path)
        if metadata.get('format').get('width'):
            return metadata.get('format').get('width')
        else:
            for i in metadata.get('streams'):
                if i.get('width'):
                    return i.get('width')

    @classmethod
    def get_height(cls, file_path):
        metadata = cls.get_metadata(file_path)
        if metadata.get('format').get('height'):
            return metadata.get('format').get('height')
        else:
            for i in metadata.get('streams'):
                if i.get('height'):
                    return i.get('height')

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
            file_path = os.path.join(file_dir, file_title + "-" + suffix + '_' +
                                     str(suffix_number) + "." + file_format)
            while os.path.exists(file_path):
                suffix_number += 1
                file_path = os.path.join(file_dir, file_title + "-" + suffix + '_' +
                                         str(suffix_number) + "." + file_format)
            log.info('file_path', file_path)
            open(file_path, encoding='utf-8', mode='x')
        except Exception as e:
            raise
        else:
            pass
        finally:
            if lock:
                lock.release()
        log.info('create_file_path', file_path)
        return file_path

    @property
    def order_metadata(self):
        '''生成获取视频元数据的命令行执行order(List); 同时生成 keywords_list;
        :return(List): 命令行执行order。
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
    @decorator.Executor_v2()
    def reverse(self):
        '''反转视频
        '''
        return [
            '-vf', 'reverse',
            '-aspect', '3:2',
            '-c:v', 'libx265',
            '-pix_fmt', 'yuv420p10le',
            '-threads', '0',
            '-tag:v', 'hvc1',
            '-x265-params',
            'crf=22',
            '-an',
            '-metadata', 'creation_time="2020-08-11T21:30:32"',
            '-color_primaries', '9',
            '-colorspace', '9',
            '-color_range', '2',
            '-color_trc', '14',
        ]

    @decorator.Timekeep()
    @decorator.Executor_v2()
    def combine(self, logo_path='/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png', logo_transparent=0.3, audio_path=None, audio_defer=0, fade_duration=1, crop='1080p', crop_y=0, reverse=False, ):
        '''添加声音 同时设置淡入淡出 及过度时长
        :param: audio_path(str): 声音文件路径
        :param: audio_defer(number): 声音文件截取处（单位/秒）
        :param: fade_duration(number): 淡入淡出过度时长（单位/秒，默认值：1）
        :param: reverse(boolean): 是否反转视频流
        '''

        order = []
        # filter_complex = "[1:a]afade=t=in:st=0:d=" + str(fade_duration) \
        # + ",afade=t=out:st=" + str(float(self.duration) - 1) \
        # + ":d=" + str(fade_duration)

        filter_complex = []

        if logo_path:
            order.extend([
                '-i', logo_path,
            ])
            filter_complex.extend([
                '[1:v][0:v]scale2ref=h=ow/mdar:w=iw/9[logo][video]',
                '[logo]format=argb,colorchannelmixer=aa=' +
                str(logo_transparent) + '[logo]',
                '[video][logo] overlay=(main_w-w)*0.7:(main_h-h)*0.7',
            ])
        if audio_path:
            audio_defer = str(audio_defer)
            fade_duration = str(fade_duration)
            order.extend([
                '-ss', audio_defer,
                '-t', str(float(self.duration)),
                '-i', audio_path,
            ])
            filter_complex.extend([
                # '[0:a]aeval=0:c=same[audio]',
                '[2:a]afade=t=in:st=0:d=' + fade_duration +
                ',afade=t=out:st=' + str(float(self.duration) - 1)
                + ':d=' + fade_duration + ',volume=12dB',
                # '[audio][music]amix=inputs=2:duration=shortest:dropout_transition=2',
            ])

        # vf = []
        video_step_one = []
        # if reverse:
        #     # 反转视频流
        #     vf.extend(['reverse'])
        if crop:
            # 画面裁剪 crop=width:height:x:y width:height表示裁剪后的尺寸
            # x:y表示裁剪区域的左上角坐标
            # '-vf', 'crop=1920:1080:0:0',
            # '-vf', 'crop=4096:2160:0:288',
            # vf.extend(['crop=1920:1080:0:200'])
            resolution = {
                '1080p': '1920:1080',
                '4k': '4096:2160',
            }
            # xy = ''
            xy = ':0:' + str(crop_y)
            ret = resolution.get(crop) + xy

            video_step_one.append('crop=' + ret)
        if reverse:
            video_step_one.append('reverse')

        if video_step_one:
            print('filter_complex', filter_complex)
            filter_complex[
                0] = '[1:v][video_step_one]scale2ref=h=ow/mdar:w=iw/9[logo][video]'
            filter_complex.insert(
                0, '[0:v]' + ','.join(video_step_one) + '[video_step_one]')

        # if vf:
        #     # 反转视频流及相关视频压缩控制（为了兼容apple设备）
        #     order.extend([
        #         '-vf', ','.join(vf),

        #         # 视频编码
        #         '-c:v', 'libx265',
        #     ])
        # else:
        #     # 若无需反转 则对video类型文件直接copy 不重新编码
        #     order.extend([
        #         '-c:v', 'copy',
        #         # '-c:v', 'libx265',
        #         # '-c', 'copy',
        #     ])

        order.extend([
            '-filter_complex', ';'.join(filter_complex),

            # 时长取最短的media
            # '-shortest',
        ])

        order.extend([
            # 长宽比约束
            # '-aspect', '16:9',

            # '-pix_fmt', 'yuv420p10le',
            # '-threads', '0',
            # '-tag:v', 'hvc1',

            '-x265-params',
            # 视频质量范围（1-51） 8为Ultra Hight 22为Low
            'crf=22',

            # 禁掉源文件中的音频
            # '-an',

            # '-metadata','creation_time="2020-08-11T21:30:32"',

            # 颜色
            '-color_primaries', '9',
            '-colorspace', '9',
            '-color_range', '2',
            '-color_trc', '14',
        ])

        # print('order', order)
        return order

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

    @decorator.Timekeep()
    @decorator.Executor()
    def trim(self, time=(), suffix_number=1, lock=None):
        '''截取视频指定某一段时间
        :param: times(tuple): ("00:26:56", "00:28:36")
        :param: suffix_number(number): 1
        '''
        if not time:
            return False
        trim_file_path = self.create_file_path(
            self.file_path, suffix='trim', suffix_number=suffix_number, lock=lock)

        log.warning('线程:%s, 父进程:%s, <Task (%s) start...>, %s' % (threading.current_thread(
        ).getName(), os.getpid(), sys._getframe().f_code.co_name, trim_file_path))

        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend([

            # 截取时间
            '-ss', time[0],
            '-to', time[1],

            # 使用copy后 避免太过于精确切割而丢失帧
            '-accurate_seek',

            '-i', self.file_path,

            # 线程(设置为4效率最高，但通用性待验证)
            # '-threads', '4',

            # 对video类型文件设置编码类型
            # 注意：copy会带来前面一段时间丢帧问题并且无预览图
            # '-c', 'copy',
            # '-c:a', 'copy',
            # '-c:v', 'copy',

            # 若voice copy失败
            '-c:v', 'copy',
            '-c:a', 'copy',
            # '-acodec', 'aac',

            # '-avoid_negative_ts', '1',
            trim_file_path])
        return {'path': trim_file_path}

    def multi_trim(self, times=()):
        '''批量截取
        :param: times(tuple): ("00:26:56", "00:28:36")
        '''
        if not time:
            return False
        for time in times:
            # self.trim(ss=time[0], to=time[1])
            self.trim(time)

    @classmethod
    def compress(cls, *args, file_path='', bit_rate=800000):
        '''文件体积压缩
        :param: future(Object future): future.result()返回一个dict，其中path键对应待压缩文件路径。
        :param: file_path(number): 压缩比特率，默认800，单位k。
        :param: bit_rate(number): 压缩比特率，默认800，单位k。
        '''

        @decorator.timekeep
        @decorator.executor
        def compress():

            log.warning('线程:%s, 父进程:%s, <Task (%s) start...>, %s' % (threading.current_thread(
            ).getName(), os.getpid(), sys._getframe().f_code.co_name, compress_file_path))

            order = copy.deepcopy(cls.__order_prefix)
            order.extend([
                '-i', file_path,
                '-s', str(width) + 'x' + str(height),
                '-aspect', str(width) + ':' + str(height),
                '-threads', '0',
                '-c:v', 'hevc_videotoolbox',
                '-r', '24.00',
                '-pix_fmt', 'yuv420p',
                '-b:v', str(bit_rate),
                '-maxrate', str(bit_rate + 200000),
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

                # ffmpeg can automatically determine the appropriate format
                # from the output file name, so most users can omit the -f
                # option.
                '-f', 'mp4',

                '-map', '0:0',
                '-map', '0:1',
                '-map_chapters', '0',
                '-max_muxing_queue_size', '40000',
                '-map_metadata', '0',
                compress_file_path])
            return order

        if args:
            future = args[0]
            file_path = future.result().get('path')
        elif file_path:
            file_path = file_path.strip()
        else:
            raise

        print('compress', file_path)
        metadata = cls.get_metadata(file_path)
        width = 640
        origin_width = cls.get_width(file_path)
        origin_height = cls.get_height(file_path)
        # log.warning('origin_width', origin_width)
        rate = float(width / float(origin_width))
        origin_bit_rate = metadata.get('streams')[0].get(
            'bit_rate') or metadata.get('format').get('bit_rate')
        origin_bit_rate = int(origin_bit_rate)

        # 若源文件分辨率宽度<640 或 源文件bit_rate<800000，则跳过压缩
        if rate < 1 or bit_rate < origin_bit_rate:
            # if True:
            height = int(rate * float(origin_height))
            log.info('compress width height', rate, metadata.get('streams')[0].get(
                'width'), metadata.get('streams')[0].get('height'), width, height)

            # file_dir, file_title, file_format = cls.get_file_info(file_path)
            compress_file_path = cls.create_file_path(
                file_path, suffix='compress', lock=cls.__lock)

            ret = compress()
        else:
            return False

        return compress_file_path

    @classmethod
    @decorator.Timekeep()
    def multi_trim(cls, files=[], callback_list=[]):
        '''多线程批量文件截取
        :param: files(List): 待剪切文件列表。
            [
                {
                    'path':'/Users/nut/Downloads/RS/CCAV.mp4',
                    'trim_times':(
                        ("00:50:22", "01:03:27"),
                        ("01:19:39", "01:37:04"), ...
                    )
                }...
            ]
        :param: callback_list(List): 处理完文件剪切后的回调函数列表。
            ['compress', ...]
        '''

        log.warning('线程:%s, 父进程:%s, <Task (%s) start...>' % (
            threading.current_thread().getName(), os.getpid(), sys._getframe().f_code.co_name))

        executor = BoundedExecutor(0, 5)

        for file in files:
            suffix_number = 0
            for time in file.get('trim_times'):
                suffix_number += 1
                log.info(sys._getframe().f_code.co_name,
                         'suffix_number', suffix_number)
                future = executor.submit(cls(file.get(
                    'path')).trim, time=time, suffix_number=suffix_number, lock=executor.lock)
                for callback in callback_list:
                    future.add_done_callback(getattr(cls, callback))
                log.info(sys._getframe().f_code.co_name,
                         'time, suffix_number', time, suffix_number)
            # executor.shutdown(wait=True)

    @classmethod
    @decorator.Timekeep()
    def multi_compress(cls, path='', callback_list=[]):
        '''多线程批量文件压缩
        :param: files(List): 
        :param: callback_list(List): 
        '''

        log.warning('父进程:%s, 线程:%s, <Task (%s) start...>' % (
            os.getpid(), threading.current_thread().getName(), sys._getframe().f_code.co_name))

        executor = BoundedExecutor(0, 5)

        path = path.strip()
        if os.path.isdir(path):
            file_path_list = os.listdir(path)
        log.info(sys._getframe().f_code.co_name,
                 'file_path_list', file_path_list)

        for file_path in file_path_list:
            future = executor.submit(
                cls.compress, file_path=os.path.join(path, file_path))
            log.info(sys._getframe().f_code.co_name,
                     'file_path', file_path, future)
            for callback in callback_list:
                future.add_done_callback(getattr(cls, callback))
        executor.shutdown(wait=True)

    def test(self, future):
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
            *args, **kwargs)
        # task.add_done_callback(callback)
        # cls.__queue.put(task)

        cls.__thread_pool.shutdown(wait=True)

        # result = futures.wait(cls.__queue, return_when=futures.ALL_COMPLETED)
        log.info('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe(
        ).f_code.co_name, threading.current_thread().getName(), os.getpid()))

    def transcode(self):
        log.info('<All done!!!> 任务:%s, 线程:%s, 父进程:%s' % (sys._getframe(
        ).f_code.co_name, threading.current_thread().getName(), os.getpid()))
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
