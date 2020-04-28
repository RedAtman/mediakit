import re
import time
import subprocess
import copy
import functools

from utils import translate


def execute():
    """
    执行shell命令（用于类方法的装饰器）
    """
    def _dec(func):
        def _func(self, *args, **kwargs):
            func(self, *args, **kwargs)
            print('after', self.order)
            ret = subprocess.run(self.order)
            # ret = subprocess.Popen(
            # self.order, shell=False, stdout=subprocess.PIPE).stdout
            print('执行结果：', ret)
        return _func
    return _dec


class Audio(object):
    """docstring for Audio"""

    def __init__(self, cls):
        # self.arg = arg
        print('cls', type(cls), cls)


class Media(object):
    """docstring for Media"""

    def __init__(self, path, title=None, author=None, camera=None, lens=None, keywords=None):
        # self.title = '一枚量子的延时摄影作品'
        # self.author = ['一枚量子']
        # self.keywords = []
        self.path = path
        self.dir, self.name, self.format = re.findall(
            '(.*)\/([^<>/\\\|:""\*\?]+)\.(\w+)$', self.path)[0]
        self.audio = {
            "path": {"input": ""}
        }
        self.title = title or self.name
        self.author = author
        self.camera = camera
        self.lens = lens
        self.keywords = keywords
        self.order_prefix = ['ffmpeg', '-y', '-loglevel', 'debug']

    @property
    def duration(self):
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of",
                                 "default=noprint_wrappers=1:nokey=1", self.path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        return float(result.stdout)

    @property
    def output_path(self):
        time_str = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        # path = self.dir + "/_" + self.title + "_" + \
        #     str(int(round(time.time() * 1000))) + "." + self.format
        path = self.dir + "/_" + self.title + "_" + \
            time_str + "." + self.format
        print('output path', path)
        return path

    # @property
    # def metadata(self):
    #     '''
    #     doc: 生成视频元数据;
    #     :params
    #         title: string, 视频标题;
    #         keywords: dict{key:list} / list, 视频关键词;
    #         author: list, 视频作者;
    #     '''
    #     meta_key_list = ['title', 'author', 'camera', 'lens', 'keywords']
    #     metadata = []
    #     for key in meta_key_list:
    #         meta = getattr(self, key)
    #         # meta_en = translate.result(meta)
    #         if isinstance(meta, str):
    #             metadata.extend(['-metadata', str(key) + '=' + meta])
    #         if isinstance(meta, list):
    #             metadata.extend(['-metadata', str(key) + '=' + " ".join(meta)])
    #         # 若是dict 则拼接values
    #         if isinstance(meta, dict):
    #             from functools import reduce

    #             def concat(a, b):
    #                 print('concat', type(a), type(b))
    #                 a.extend(b)
    #                 return a

    #             meta_concat = reduce(concat, list(meta.values()))
    #             print('meta_concat', meta_concat)

    #             metadata.extend(
    #                 ['-metadata', str(key) + '=' + " ".join(meta_concat)])

    #     return metadata

    @execute()
    def metadata(self):
        """
        读取现有文件的元数据 并保存为txt文件
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
            images_path + '/output_' + bit_rate + '.mov'])

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
