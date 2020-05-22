import re
import time
import subprocess
import copy
import functools
import os

from utils import translate


def execute():
    """
    执行shell命令（用于类方法的可调用self的装饰器）
    """
    def _dec(func):
        def _func(self, *args, **kwargs):
            func(self, *args, **kwargs)
            start_time = time.time()
            print('after', start_time, self.order)
            ret = subprocess.run(self.order)
            # ret = subprocess.Popen(
            # self.order, shell=False, stdout=subprocess.PIPE).stdout

            duration = time.time() - start_time
            print('耗时', duration, '执行结果：', ret)
        return _func
    return _dec


class Audio(object):
    """docstring for Audio"""

    def __init__(self, cls):
        # self.arg = arg
        print('cls', type(cls), cls)


class Media(object):
    """docstring for Media"""

    def __init__(self, path, title=None, artist=None, category=None, camera=None, lens=None, keywords=None):
        """
        :params
            title: string, 视频标题;
            keywords: dict{key:list} / list, 视频关键词;
            artist: list, 视频作者;
        """
        self.path = path
        self.dir, self.name, self.format = re.findall(
            '(.*)\/([^<>/\\\|:""\?]+)\.(\w+)$', self.path)[0]
        self.audio = {
            "path": {"input": ""}
        }
        self.title = title or self.name
        self.artist = artist
        self.album_artist = artist
        self.category = category
        self.camera = camera
        self.lens = lens
        self.keywords = keywords
        self.keywords_list = []
        self.order_prefix = ['ffmpeg', '-y', '-loglevel', 'debug']

    @property
    def duration(self):
        """ 媒体时长（单位/s）
        """
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of",
            "default=noprint_wrappers=1:nokey=1", self.path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return float(result.stdout)

    @property
    def output_path(self):
        """ 媒体输出路径
        """
        time_str = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        # path = self.dir + "/_" + self.title + "_" + \
        #     str(int(round(time.time() * 1000))) + "." + self.format
        path = self.dir + "/_" + self.title + "_" + \
            time_str + "." + self.format
        print('output path', path)
        return path

    @property
    def trim_path(self):
        """ str 媒体剪切片段输出路径
        """
        num = 1
        path = self.dir + "/" + self.title + "_trim_" + \
            str(num) + "." + self.format
        while os.path.exists(path):
            num += 1
            path = self.dir + "/" + self.title + "_trim_" + \
                str(num) + "." + self.format
        return path

    @property
    def order_metadata(self):
        '''
        doc: 生成视频元数据order; 同时生成keywords_list;
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
                self.keywords_list.append(meta)
            if isinstance(meta, list):
                order_metadata.extend(
                    ['-metadata', str(key) + '=' + ",".join(meta)])
                # print('meta', type(meta), meta)
                self.keywords_list.extend(meta)
            # 若是dict 则拼接values
            if isinstance(meta, dict):
                from functools import reduce

                def concat(a, b):
                    print('concat', type(a), type(b))
                    a.extend(b)
                    return a

                meta_concat = reduce(concat, list(meta.values()))
                print('meta_concat', meta_concat)

                order_metadata.extend(
                    ['-metadata', str(key) + '=' + ",".join(meta_concat)])
                self.keywords_list.extend(meta_concat)
        # print('order_metadata,self.keywords_list', order_metadata,self.keywords_list)

        # print('translate',translate.translate,dir(translate.translate))
        keywords_en_list = translate.translate.result(self.keywords_list)
        self.keywords_list.extend(keywords_en_list)
        self.keywords_list = [i.strip() for i in self.keywords_list]
        print('keywords_list-----', self.keywords_list)
        order_metadata.extend(
            ['-metadata', 'keywords' + '=' + ",".join(self.keywords_list)])
        print('order_metadata', order_metadata)

        return order_metadata

    @property
    @execute()
    def metadata(self):
        """
        媒体元数据
        """
        self.order = ['ffprobe', '-v', 'quiet', '-show_format',
                      '-show_streams', '-print_format', 'json', self.path]

    @execute()
    def save_metadata(self):
        """
        读取现有文件的元数据 并保存为txt文件
        """
        self.order = copy.deepcopy(self.order_prefix)
        metadata_path = self.dir + "/_" + self.title + ".txt"
        self.order.extend(['-i', self.path,
                           '-f', 'ffmetadata', metadata_path])

    @execute()
    def set_metadata(self):
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend(['-i', self.path])
        self.order.extend(self.order_metadata)
        self.order.extend(['-c:a', 'copy',
                           '-c:v', 'copy',
                           self.output_path])

    @execute()
    def add_voice(self, audio_path, audio_defer, fade_duration=1):
        """
        添加声音 同时设置淡入淡出 及过度时长
        :param: audio_path: 声音文件路径
        :param: audio_defer: 声音文件截取处（单位/秒）
        :param: fade_duration: 淡入淡出过度时长（单位/秒，默认值：1）
        """
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

    @execute()
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

    @execute()
    def delete_voice(self):
        """
        去除声音（静音）
        """
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend(['-i', self.path])
        # order.extend(self.metadata)
        self.order.extend(['-an',
                           '-c:v', 'copy',
                           self.output_path])

    @execute()
    def trim(self, ss="00:00:00", to="00:00:01"):
        """
        截取视频指定某一段时间
        """
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend([

            # 截取时间
            '-ss', ss,
            '-to', to,

            # 使用copy后 避免太过于精确切割而丢失帧
            '-accurate_seek',

            '-i', self.path,

            # 线程(待验证)
            # '-threads', '4',

            # 对video类型文件设置编码类型
            # 注意：copy会带来前面一段时间丢帧问题并且无预览图
            # '-c', 'copy',
            # '-c:a', 'copy',
            # '-c:v', 'copy',

            # 若voice copy失败
            '-c:v', 'copy',
            '-acodec', 'aac',

            # '-avoid_negative_ts', '1',
            self.trim_path])

    @execute()
    def decode(self, format='mov'):
        """
        截取视频指定某一段时间
        """
        self.order = copy.deepcopy(self.order_prefix)
        self.order.extend([
            '-i', self.path,

            # 线程(待验证)
            # '-threads', '4',

            # '-avoid_negative_ts', '1',
            self.dir + "/" + self.title + "_decode_." + format])

    def trim_mul(self, times=(("00:00:00", "00:00:01"))):
        for time in times:
            self.trim(ss=time[0], to=time[1])

    def concat(self):

        return 'ffmpeg -f concat -i concat.txt -c copy concat.mov'
