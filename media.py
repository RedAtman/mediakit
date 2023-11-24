import functools
import json
import os
import sys
import threading
import time

from base import BaseMedia
from config import config
from logger import logger
from utils import BoundedExecutor, Dict2Obj, Translator, decorator, exceptions, execute


class Audio:
    '''docstring for Audio'''

    def __init__(self, cls):
        # self.arg = arg
        print('cls', type(cls), cls)

    @classmethod
    def trim(cls):
        command = 'ffmpeg -y -i /Users/nut/Downloads/Father.m4a -c copy -ss 00:02:43.00 -to 00:51:56 output.m4a'.strip()
        return command


class Media(BaseMedia):
    # __thread_pool = futures.ThreadPoolExecutor(max_workers=64)
    # __queue = queue.Queue(maxsize=0)
    __lock = threading.Lock()
    __loglevel = config.LOG_LEVEL.lower()

    ffmpeg_prefix = [
        'ffmpeg', '-y',
        '-loglevel', __loglevel,
        # '-i', self.path,
    ]

    def __init__(
        self,
        *args,
        title=None,
        artist='',
        category=None,
        camera=None,
        lens=None,
        keywords=None,
        **kwargs
    ):
        '''
        Keyword Arguments:
            title {[type]} -- [视频标题] (default: {None})
            artist {str} -- [视频作者] (default: {''})
            category {[str]} -- [description] (default: {None})
            camera {[str]} -- [description] (default: {None})
            lens {[str]} -- [description] (default: {None})
            keywords {[dict{key:list} / list]} -- [视频关键词] (default: {None})
            loglevel {str} -- [日志级别] (default: {'info'})
        '''
        super().__init__(*args, **kwargs)
        self.artist = artist
        self.album_artist = artist
        self.category = category
        self.camera = camera
        self.lens = lens
        self.keywords = keywords
        self.keywords_list = set()

    @functools.cached_property
    def output_path(self):
        '''Media output path'''
        return self.get_output_path()

    def get_output_path(self, suffix=''):
        '''媒体输出路径(代替 self.output_path)

        Keyword Arguments:
            suffix {str} -- [输出文件名后缀] (default: {''})

        Returns:
            [str] -- [媒体输出路径]
        '''
        # suffix or caller function name
        suffix = suffix or sys._getframe().f_back.f_code.co_name
        return f'{self.dirname}/_{self.title}_{suffix}_{time.strftime("%Y%m%d%H%M%S", time.localtime())}.{self.ext}'

    @classmethod
    def create_file_path(cls, path, suffix='suffix', suffix_number=1, lock=None):
        '''产生媒体剪切片段输出路径

        Arguments:
            path {[type]} -- [description]

        Keyword Arguments:
            suffix {str} -- [description] (default: {'suffix'})
            suffix_number {number} -- [description] (default: {1})
            lock {[type]} -- [description] (default: {None})

        Returns:
            [type] -- [description]
                e.g.: /Users/nut/Downloads/RS/_trim/VIDEO_trim_1.mp4
        '''
        dirname, title, ext = cls.get_file_info(path)
        dirname = os.path.join(dirname, '_' + suffix)
        if not os.path.exists(dirname):
            try:
                os.mkdir(dirname)
            except FileExistsError:
                os.makedirs(dirname)
            except OSError as err:
                logger.exception(err)
                # os.makedirs(self.save_dir)
                raise err
            except Exception as err:
                logger.exception(err)
                raise err

        if cls.__lock:
            cls.__lock.acquire()
        try:
            suffix_number = suffix_number or 1
            file_path = os.path.join(dirname, f'{title}-{suffix}_{suffix_number}.{ext}')
            while os.path.exists(file_path):
                suffix_number += 1
                file_path = os.path.join(dirname, f'{title}-{suffix}_{suffix_number}.{ext}')
            open(file_path, encoding='utf-8', mode='x')
        except Exception as err:
            logger.exception(err)
            raise err
        finally:
            if cls.__lock:
                cls.__lock.release()
        logger.info('create_file_path: %s', file_path)
        return file_path

    @functools.cached_property
    def order_metadata(self):
        '''生成获取视频元数据的命令行执行order(List); 同时生成 keywords_list;

        Returns:
            [list] -- [命令行执行order]
        '''
        meta_key_list = [
            'title', 'artist', 'album_artist', 'category', 'camera', 'lens', 'keywords'
        ]
        order_metadata = []
        for key in meta_key_list:
            meta = getattr(self, key)
            if not meta:
                continue

            if isinstance(meta, str):
                order_metadata.extend(['-metadata', str(key) + '=' + meta])
                self.keywords_list.add(meta)
            if isinstance(meta, list):
                order_metadata.extend(
                    ['-metadata', str(key) + '=' + ",".join(meta)])
                self.keywords_list.update(meta)
            # 若是dict 则拼接values
            if isinstance(meta, dict):

                def concat(a, b):
                    logger.info(('concat', type(a), type(b)))
                    a.extend(b)
                    return a

                meta_concat = functools.reduce(concat, list(meta.values()))

                order_metadata.extend(
                    ['-metadata', str(key) + '=' + ",".join(meta_concat)])
                self.keywords_list.update(meta_concat)

        keywords_en_list = Translator.translate(self.keywords_list)
        self.keywords_list.update(keywords_en_list)
        self.keywords_list = {i.strip() for i in self.keywords_list}

        order_metadata.extend(
            ['-metadata', 'keywords' + '=' + ",".join(self.keywords_list)])

        return order_metadata

    @decorator.timer
    def save_metadata(self):
        '''Save metadata to file(txt).
        '''
        return [
            '-f', 'ffmetadata',
            self.dirname + "/" + self.title + '_metadate' + ".txt",
        ]

    @decorator.timer
    def set_metadata(self):
        '''Set metadata to file.
        '''
        return self.order_metadata.extend([
            self.order_metadata,
            '-c:a', 'copy',
            '-c:v', 'copy',
            self.get_output_path(suffix='set_metadata'),
        ])

    @decorator.timer
    def reverse(self):
        '''Reverse video stream.
        '''
        new_file_path = self.get_output_path(suffix='reverse')
        command = self.ffmpeg_prefix.copy()
        command.extend([
            '-i', self.path,
            '-vf', 'reverse',
            # '-aspect', '3:2',
            '-aspect', '16:9',
            '-c:v', 'libx265',
            '-pix_fmt', 'yuv420p10le',
            '-threads', '0',
            '-tag:v', 'hvc1',
            '-x265-params',
            'crf=22',
            '-an',
            # '-metadata', 'creation_time="2020-08-11T21:30:32"',
            '-metadata', f'creation_time={time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())}',
            # '-color_primaries', '9',
            # '-colorspace', '9',
            # '-color_range', '2',
            # '-color_trc', '14',
            new_file_path,
        ])
        # command.extend([
        #     '-i', self.path,
        #     '-vf', 'reverse',
        #     '-aspect', '16:9',
        #     '-c:v', 'libx265',
        #     '-pix_fmt', 'yuv420p10le',
        #     '-tag:v', 'hvc1',
        #     '-x265-params',
        #     '-crf', '22',
        #     '-an',
        #     # '-preset', 'veryfast',
        #     # '-c:a', 'copy',
        #     # '-c:v libx264 -c:a -strict experimental',
        #     # '-pix_fmt', 'yuv420p10le',
        #     # '-movflags', '+faststart',
        #     '-color_primaries', '9',
        #     '-colorspace', '9',
        #     '-color_range', '2',
        #     '-color_trc', '14',
        #     new_file_path,
        # ])
        execute(command)
        return Media(path=new_file_path)

    @decorator.timer
    def combine(
        self,
        watermark_path='/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png',
        watermark_transparent=0.3,
        audio_path=None,
        audio_defer: float = 0,
        fade_duration: float = 1,
        crop='1080p',
        crop_y=0,
        reverse=False,
    ):
        '''视频混合处理:
            - 添加logo并设置透明度
            - 添加音频并设置淡入淡出及过度时长
            - 视频剪切尺寸及y轴偏移量
            - 反转视频流

        Keyword Arguments:
            watermark_path {str} -- [logo文件路径] (default: {'/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png'})
            watermark_transparent {float} -- [logo透明度 范围: 0-1] (default: {0.3})
            audio_path {str} -- [背景音频文件路径] (default: {None})
            audio_defer {int/float} -- [背景音频文件截取处 单位:秒] (default: {0})
            fade_duration {int/float} -- [淡入淡出过度时长 单位:秒] (default: {1})
            crop {str} -- [视频剪切尺寸 可选: 1080p,4k] (default: {'4k'})
            crop_y {int} -- [视频剪切y轴偏移量] (default: {0})
            reverse {bool} -- [是否反转视频流 备注: reverse=True时真正开始处理视频流需要消耗一段时间] (default: {False})

        Returns:
            [type] -- [description]
                e.g.:
        '''

        command = self.ffmpeg_prefix.copy()
        filter_complex = []

        if watermark_path:
            command.extend([
                '-i', watermark_path,
            ])
            filter_complex.extend([
                '''atempo=2,[1:v][0:v]scale2ref=h=ow/mdar:w=iw/9[logo][video]''',
                '''[logo]format=argb,colorchannelmixer=aa=''' +
                str(watermark_transparent) + '[logo]',
                '''[video][logo] overlay=(main_w-w)*0.7:(main_h-h)*0.7''',
            ])
        if audio_path:
            audio_defer = str(audio_defer)
            fade_duration = str(fade_duration)
            command.extend([
                '-ss', audio_defer,
                '-t', str(float(self.duration)),
                '-i', audio_path,
            ])
            filter_complex.extend([
                # '[0:a]aeval=0:c=same[audio]',
                '[2:a]afade=t=in:st=0:d=' + fade_duration + ',afade=t=out:st=' + \
                str(float(self.duration) - 1) + ':d=' + \
                fade_duration + ',volume=12dB',
                # '[audio][music]amix=inputs=2:duration=shortest:dropout_transition=2',
            ])

        # vf = []
        video_step_one = []
        if crop:
            # 画面裁剪 crop=width:height 或 # crop=width:-1
            # 画面裁剪 crop=width:height:x:y width:height表示裁剪后的尺寸
            # x:y表示裁剪区域的左上角坐标
            # '-vf', 'crop=1920:1080:0:0',
            # '-vf', 'crop=4096:2160:0:288',
            # vf.extend(['crop=1920:1080:0:200'])
            resolution = {
                '1080p': [1920, 1080],
                '4k': [4096, 2160],
                # '4k': '4096:2304',
                # '4k': '4096:2736'
            }
            xy = [0, crop_y]
            ret = resolution.get(crop) + xy

            # video_step_one.append(
            #     'scale=' + '4096:-1' + '[video_step_zero];[video_step_zero]' + 'crop=' + ':'.join(map(lambda x: str(x), ret)))
            video_step_one.append(
                f'scale=4096:-1[video_step_zero];[video_step_zero]crop={":".join(map(str, ret))}'
            )

        if reverse:
            video_step_one.append('reverse')

        if video_step_one:
            # print('filter_complex', filter_complex)
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

        command.extend([
            '-filter_complex', ';'.join(filter_complex),

            # 时长取最短的media
            # '-shortest',
        ])

        new_file_path = self.get_output_path(suffix='combine')
        command.extend([
            # 长宽比约束
            # '-aspect', '16:9',

            # '-pix_fmt', 'yuv420p10le',
            # '-threads', '0',
            # '-tag:v', 'hvc1',

            '-x265-params',

            # 视频质量范围（1-51） 8为Ultra Hight 22为Low
            'crf=8',

            # 禁掉源文件中的音频
            # '-an',

            # '-metadata','creation_time="2020-08-11T21:30:32"',

            # 颜色

            # 最高参数 似乎一样
            # '-color_primaries', '22',
            # '-colorspace', '11',
            # '-color_trc', '18',

            '-color_primaries', '9',
            '-colorspace', '9',
            '-color_trc', '14',
            '-color_range', '2',

            # 视频码率
            # '-b:v', '4000k',

            # 视频速度调整
            # '-vf', "setpts=0.5*PTS",

            # 对音频速度调整限制在0.5 到 2.0 之间（即半速或倍速）
            # '-af', "atempo=2.0",

            new_file_path,
        ])

        execute(command)
        return Media(path=new_file_path)

    @decorator.timer
    def images_to_video(self, images_path, image_format, bit_rate='5000k'):
        create_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        new_file_path = f'{images_path}/output_{bit_rate}_1920_{create_time}.mp4'
        command = self.ffmpeg_prefix.copy()
        command.extend([
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
            new_file_path,
        ])
        execute(command)
        return Media(path=new_file_path)

    @decorator.timer
    def delete_voice(self):
        '''silence audio.'''
        return [
            '-an',
            '-c:v', 'copy',
            self.get_output_path(suffix='delete_voice'),
        ]

    @decorator.timer
    def trim(self, time=(), suffix_number=1, lock=None):
        '''截取视频指定某一段时间

        Keyword Arguments:
            time {tuple} -- {截取时间段} (default: {()})
                e.g.: ("00:26:56", "00:28:36")
            suffix_number {number} -- 1 (default: {1})
            lock {[type]} -- 新建文件名时用 (default: {None})

        Returns:
            bool -- [description]
        '''
        if not isinstance(time, (tuple, list)) and len(time) != 2:
            raise ValueError('参数[time]必须为长度为2的tuple或list')
        ss, to = time

        new_file_path = self.create_file_path(
            self.path, suffix='trim', suffix_number=suffix_number, lock=lock)

        command = self.ffmpeg_prefix.copy()
        command.extend([
            # 截取时间
            '-ss', ss,
            '-to', to,

            # 使用copy后 避免太过于精确切割而丢失帧
            '-accurate_seek',

            '-i', self.path,

            # 线程(设置为4效率最高, 但通用性待验证)
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
            new_file_path
        ])
        execute(command)
        return Media(path=new_file_path)

    @decorator.timer
    def compress(self):
        width, height = self.width_height
        bitrate = 3200000 / 1280 / 720
        bitrate = bitrate * width * height
        # logger.warning('bitrate: %s, self.bitrate: %s', bitrate, self.bitrate)
        if bitrate >= self.bitrate:
            logger.warning('bitrate: %s, self.bitrate: %s', bitrate, self.bitrate)
            # bitrate = self.bitrate
            # raise ValueError(f'output bit_rate({bitrate}) must < origin bit_rate({self.bitrate})')
        return self._compress(width=width, height=height, bitrate=bitrate)

    def _compress(
        self,
        width=1280,
        height=720,
        # bitrate=1600000,
        bitrate=3200000.00,
    ):
        '''压缩视频

        Keyword Arguments:
            width {int} -- [压缩分辨率宽度 单位px] (default: {1280})
            height {int} -- [压缩分辨率高度 单位px] (default: {720})
            bitrate {int} -- [压缩码率 单位kb/s] (default: {3200000})

        Returns:
            [type] -- [description]
        '''
        # origin_width, origin_height = self.width_height
        # origin_bit_rate = self.bitrate

        # # 若制定压缩分辨率width>源文件分辨率width 或 制定压缩bit_rate>=源文件bit_rate 则跳过压缩
        # if width > origin_width:
        #     raise ValueError(f'output width({width}) must < origin_width({origin_width})')
        # if bit_rate >= origin_bit_rate:
        #     raise ValueError(f'output bit_rate({bit_rate}) must < origin_bit_rate({origin_bit_rate})')

        # # 计算压缩比例
        # zoom_ratio = float(width / origin_width)
        # height = int(zoom_ratio * origin_height)

        # logger.warning(
        #     'Thread: %s, Parent Process: %s, Function: %s',
        #     threading.current_thread().name, os.getpid(),
        #     sys._getframe().f_code.co_name
        # )

        new_file_path = self.create_file_path(
            self.path,
            suffix='compress',
            lock=self.__lock,
        )
        command = self.ffmpeg_prefix.copy()
        command.extend([
            '-i', self.path,
            '-s', str(width) + 'x' + str(height),
            '-aspect', str(width) + ':' + str(height),
            '-threads', '0',
            '-c:v', 'hevc_videotoolbox',
            '-r', '24.00',
            '-pix_fmt', 'yuv420p',
            '-b:v', str(bitrate),
            '-maxrate', str(bitrate + 200000),
            '-bufsize', '4M',
            '-allow_sw', '1',
            '-profile:v', 'main',
            '-vtag', 'hvc1',
            '-c:a:0', 'aac',
            '-ac:a:0', '2',
            '-ar:a:0', '32000',
            '-b:a:0', '128k',
            # '-b:a:0', '256k',
            '-strict',
            '-2',
            '-sn',

            # ffmpeg can automatically determine the appropriate format
            # from the output file name, so most users can omit the -f option.
            '-f', 'mp4',

            '-map', '0:0',
            '-map', '0:1?',
            '-map_chapters', '0',
            '-max_muxing_queue_size', '40000',
            '-map_metadata', '0',
            new_file_path,
        ])
        # logger.warning(
        #     'Thread: %s, Parent Process: %s, Function: %s, command: %s',
        #     threading.current_thread().name, os.getpid(),
        #     sys._getframe().f_code.co_name,
        #     command,
        # )
        execute(command)
        return Media(path=new_file_path)

    @classmethod
    @decorator.timer
    def multi_trim(cls, files=[], callback_list=[]):
        '''多线程批量文件截取

        Keyword Arguments:
            files {list} -- [待剪切文件配置组成的list] (default: {[]})
                [
                    {
                        'path':'/Users/nut/Downloads/RS/CCTV.mp4',
                        'trim_times':(
                            ("00:50:22", "01:03:27"),
                            ("01:19:39", "01:37:04"), ...
                        )
                    }...
                ]
            callback_list {list} -- [处理完文件剪切后的回调函数名组成的list] (default: {[]})
                ['compress', ...]
        '''
        executor = BoundedExecutor()
        for file in files:
            suffix_number = 0
            for _time in file.get('trim_times'):
                suffix_number += 1
                media = cls(file_path=file.get('path'))
                future = executor.submit(
                    getattr(media, 'trim'),
                    time=_time,
                    suffix_number=suffix_number,
                    lock=executor.lock,
                )
                for _callback in callback_list:
                    # callback = getattr(cls, _callback)
                    # future.add_done_callback(
                    #     lambda future: callback(future.result()))
                    # callback = getattr(cls, _callback)
                    future.add_done_callback(
                        lambda future: getattr(future.result(), _callback)())

        executor.shutdown(wait=True)

    @classmethod
    @decorator.timer
    def multi_compress(cls, directory='', callback_list=[]):
        '''多线程批量文件压缩

        Keyword Arguments:
            directory {str} -- [待压缩文件所在的目录绝对地址] (default: {''})
                e.g.: /usr/media/
            callback_list {list} -- [处理完文件压缩后的回调函数名组成的list] (default: {[]})
                e.g.: ['func', ...]
        '''
        executor = BoundedExecutor()
        directory = directory.strip()
        # directory = os.path.abspath(directory)
        if not os.path.isdir(rf'{directory}'):
            raise TypeError(f'Directory does not exist: {directory}')
        file_path_list = os.listdir(directory)
        for file_path in file_path_list:
            file_abspath = os.path.join(directory, file_path)
            if not os.path.isfile(file_abspath):
                continue
            file_abspath = os.path.abspath(file_abspath)
            try:
                media = cls(path=file_abspath)
            except exceptions.NotMediaException as err:
                logger.exception(err)
                continue

            try:
                future = executor.submit(media.compress)
                for callback in callback_list:
                    future.add_done_callback(getattr(cls, callback))
                future.result()
            except Exception as err:
                logger.exception(err)
        logger.info('Waiting for all subprocesses done...')
        executor.shutdown(wait=True)

    @decorator.timer
    def decode(self, format='mov'):
        '''解码视频'''
        command = self.ffmpeg_prefix.copy()
        new_file_path = self.dirname + "/" + self.title + "_decode_." + format
        command.extend([
            '-i', self.path,

            # 线程(待验证)
            # '-threads', '4',

            # '-avoid_negative_ts', '1',
            new_file_path,
        ])
        execute(command)
        return Media(path=new_file_path)

    def concat(self):

        return 'ffmpeg -f concat -i concat.txt -c copy concat.mov'


class MediaTool:
    '''Processing media files based on meta.json'''

    def __init__(self, directory):
        self.directory = directory.strip()
        self._meta = self.read_meta_json(directory)
        self.meta = Dict2Obj(self._meta)

    # @decorator.classproperty
    # def meta(cls):
    #     self.read_meta_json(directory)

    @staticmethod
    def read_meta_json(directory):
        '''读取指定dir下面meta.json文件的信息

        Arguments:
            directory {str} -- [文件夹地址]

        Returns:
            [dict] -- [media meta]
            e.g.: {
                "video": {
                    "path": "20210831_ProRes-444_BT2020L_OriRes_25_UHQ_mb05.mov",
                    "title": "20210831_中国北京天坛祈年殿",
                    "artist": "aQuantum,一枚量子",
                    "category": "time_lapse",
                    "camera": "sony_α7r2",
                    "lens": "laowa_12mm_f2.8"
                },
                "resolution": "4k",
                "reverse": False,
                "crop": {
                    "w": 4096,
                    "h": 2160,
                    "x": 0,
                    "y": 100
                },
                "audio": {
                    "path": "/Users/nut/Downloads/Illuminate (Trailer Music) - Dirk Leupolz.mp3",
                    "defer": 15.3,
                    "fade_duration": 1
                },
                "watermark": {
                    "path": "/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png",
                    "transparent": 0.3
                }
            }
        '''
        directory = directory.strip()
        if not os.path.exists(directory):
            raise FileNotFoundError('Directory not found')
        if not os.path.isdir(directory):
            raise NotADirectoryError('Not a directory')
        if not os.listdir(directory).count('meta.json'):
            raise FileNotFoundError('meta.json not found')
        try:
            with open(os.path.join(directory, 'meta.json'), 'r', encoding='utf-8') as fd:
                meta = json.loads(fd.read()).get('video', {})
        except Exception as err:
            logger.exception(err)
            raise err
        return meta

    def combine(self, ):
        media = Media(**self.meta.video._dict())
        return media.combine(
            watermark_path=self.meta.watermark.path,
            watermark_transparent=self.meta.watermark.transparent,
            audio_path=self.meta.audio.path,
            audio_defer=self.meta.audio.defer,
            fade_duration=self.meta.audio.fade_duration,
            crop=self.meta.resolution,
            crop_y=self.meta.crop.y,
            reverse=self.meta.reverse,
        )

    def trim(self, time=()):
        media = Media(**self.meta.video._dict())
        return media.trim(time=time)
