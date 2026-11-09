import functools
import logging
import time
from typing import Any, Dict, List, Optional, Set, Union

import ffmpeg

from base.media import BaseMedia
from config import CONFIG
from src.mixins.transcriber import MixinMediaTranscriber
from utils import decorator, translator
from utils.command import CommandExecutor
from utils.video import VideoResolution

from .media import BaseMedia

logger = logging.getLogger()
__all__ = ['Video']


class Video(BaseMedia, MixinMediaTranscriber):
    _INCLUDE_TYPE = ['video']

    def __init__(
        self,
        *args,
        artist: str = '',
        category: List[str] = [],
        camera: List[str] = [],
        lens: List[str] = [],
        keywords: List[str] = [],
        **kwargs,
    ):
        """
        Keyword Arguments:
            artist {str} -- [Artist] (default: {''})
            category {[str]} -- [description] (default: {None})
            camera {[str]} -- [description] (default: {None})
            lens {[str]} -- [description] (default: {None})
            keywords {[dict{key:list} / list]} -- [Video keywords] (default: {None})
            loglevel {str} -- [Log level] (default: {CONFIG.LOG_LEVEL.lower()})
        """
        super().__init__(*args, **kwargs)
        self.artist: str = artist
        self.album_artist: str = artist
        self.category: List[str] = category
        self.camera: List[str] = camera
        self.lens: List[str] = lens
        self.keywords: List[str] = keywords
        self.keywords_list: Set[str] = set()

    @functools.cached_property
    def order_metadata(self) -> List[str]:
        """生成获取视频元数据的命令行执行order(List); 同时生成 keywords_list;

        Returns:
            [list] -- [命令行执行order]
        """
        meta_key_list = ['title', 'artist', 'album_artist', 'category', 'camera', 'lens', 'keywords']
        order_metadata: List[str] = []
        for key in meta_key_list:
            meta: Union[str, list] = getattr(self, key)
            if not meta:
                continue

            if isinstance(meta, str):
                order_metadata.extend(['-metadata', str(key) + '=' + meta])
                self.keywords_list.add(meta)
            if isinstance(meta, list):
                order_metadata.extend(['-metadata', str(key) + '=' + ','.join(meta)])
                self.keywords_list.update(meta)
            # 若是dict 则拼接values
            if isinstance(meta, dict):

                def concat(a, b):
                    logger.info(('concat', type(a), type(b)))
                    a.extend(b)
                    return a

                meta_concat = functools.reduce(concat, list(meta.values()))

                order_metadata.extend(['-metadata', str(key) + '=' + ','.join(meta_concat)])
                self.keywords_list.update(meta_concat)
        keywords_en_list = translator.Translator.translate(self.keywords_list)
        self.keywords_list.update(keywords_en_list)
        self.keywords_list = {i.strip() for i in self.keywords_list}

        order_metadata.extend(['-metadata', 'keywords' + '=' + ','.join(self.keywords_list)])

        return order_metadata

    @decorator.timer
    @decorator.execute
    def save_metadata(self):
        """Save metadata to file(txt)."""
        new_file_path = self.dirname + '/' + self.title + '_metadata.txt'
        command = self._FFMPEG_PREFIX + ['-i', self.path, '-f', 'ffmetadata', new_file_path]
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def set_metadata(self):
        """Set metadata onto the video (stream copy)."""
        new_file_path = self.get_output_path(suffix='set_metadata')
        command = (
            self._FFMPEG_PREFIX
            + ['-i', self.path]
            + self.order_metadata
            + ['-c:a', 'copy', '-c:v', 'copy', new_file_path]
        )
        return self, command, new_file_path

    @property
    def fps(self):
        fps: Dict[str, Any] = self._fps()
        assert isinstance(fps, str), f'fps must be str, but got: {type(fps)}: {fps}'
        assert fps.isdigit(), f'fps must be digit, but got: {type(fps)}: {fps}'
        return float(fps)

    @decorator.timer
    def _fps(self):
        """Get video fps."""
        command = [
            self._FFPROBE_BIN,
            '-v',
            'error',
            '-select_streams',
            'v',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
            '-show_entries',
            'stream=r_frame_rate',
            self.path,
            '|',
            'bc',
            # "-l",
        ]
        return CommandExecutor.run(command, mode='pipe')

    @property
    def resolution(self) -> tuple[int, int]:
        probe = ffmpeg.probe(self.path, cmd=self._FFPROBE_BIN)
        video_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']
        if not video_streams:
            raise ValueError('No video streams found')
        return video_streams[0]['width'], video_streams[0]['height']

    @functools.cached_property
    def frames_count(self):
        try:
            command = f'{self._FFPROBE_BIN} -v error -select_streams v -show_streams "{self.path}" | grep nb_frames | sed -e s/nb_frames=//'
            result = CommandExecutor.run(command)
            return int(result)
        except Exception:
            command = f'{self._FFPROBE_BIN} -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=nokey=1:noprint_wrappers=1 "{self.path}"'
            result = CommandExecutor.run(command)
            if result.isdigit():
                return int(result)
            default_frames_count = 10000000
            logger.warning(f'Cannot get frames count: {self.path}, set to {default_frames_count}.')
            return default_frames_count

    @functools.cached_property
    def width_height(self):
        width, height = 0, 0
        _format = self.metadata.get('format')
        if _format and _format.get('width') and _format.get('height'):
            width, height = _format.get('width'), _format.get('height')
        else:
            for stream in self.metadata.get('streams'):
                if stream.get('width') and stream.get('height'):
                    width, height = stream.get('width'), stream.get('height')
                    break
        return width, height

    @functools.cached_property
    def bitrate(self):
        bitrate = self.metadata.get('streams')[0].get('bit_rate') or self.metadata.get('format').get('bit_rate')
        return float(bitrate)

    @functools.cached_property
    def duration(self):
        return self.metadata.get('streams')[0].get('duration')

    @decorator.timer
    @decorator.execute
    def reverse(self):
        """Reverse video stream."""
        new_file_path = self.get_output_path(suffix='reverse')
        command = self._FFMPEG_PREFIX + [
            '-i',
            self.path,
            '-vf',
            'reverse',
            # '-aspect', '3:2',
            '-aspect',
            '16:9',
            '-c:v',
            'libx265',
            '-pix_fmt',
            'yuv420p10le',
            # "-threads",
            # "0",
            '-tag:v',
            'hvc1',
            '-x265-params',
            'crf=22',
            '-an',
            # '-metadata', 'creation_time="2020-08-11T21:30:32"',
            '-metadata',
            f'creation_time={time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())}',
            # '-color_primaries', '9',
            # '-colorspace', '9',
            # '-color_range', '2',
            # '-color_trc', '14',
            new_file_path,
        ]
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
        return self, command, new_file_path

    # combine() 的滤镜由三段互不相干的关注点组成, 各自返回片段列表; 拼装留在 combine 里.
    # 之前是边追加边按索引改写 filter_complex[0], 于是"没有 logo 但需要裁剪"会 IndexError,
    # "没有 logo 但有音频"会把音频滤镜整条覆盖掉, 音频流编号也永远写死成 [2:a].

    def _watermark_filters(self, watermark_transparent: float, video_label: str = 'video') -> list[str]:
        """logo 缩放/上色/叠加到视频上."""
        return [
            # ponytail: 前缀 'atempo=2,' 是历史遗留 (atempo 是音频滤镜), 存在视频链时会被整条替换;
            # 保留它只为不改动"只加 logo"那一条 ffmpeg 命令
            f'atempo=2,[1:v][{video_label}]scale2ref=h=ow/mdar:w=iw/9[logo][video]',
            f'[logo]format=argb,colorchannelmixer=aa={watermark_transparent}[logo]',
            '[video][logo] overlay=(main_w-w)*0.7:(main_h-h)*0.7',
        ]

    def _audio_filters(self, fade_duration: float, input_index: int) -> list[str]:
        """背景音轨淡入/淡出并抬 12dB.

        input_index 由额外输入决定: 源视频固定是 0, logo 占 1, 音频排在它们之后.
        """
        duration = float(self.duration)
        return [
            f'[{input_index}:a]afade=t=in:st=0:d={fade_duration}'
            f',afade=t=out:st={duration - 1}:d={fade_duration}'
            ',volume=12dB'
        ]

    def _video_filters(self, crop: Optional[str], crop_y: int, reverse: bool) -> list[str]:
        """裁剪与反转; 顺序敏感, 先缩放并裁到目标尺寸, 再考虑反转."""
        steps: list[str] = []
        resolution_mapper = {'1080p': [1920, 1080], '4k': [4096, 2160]}
        resolution = resolution_mapper.get(crop) if crop else None
        if resolution:
            # crop=width:height:x:y, x:y 是裁剪区左上角; 先把宽度归一到 4096 再裁
            ret = resolution + [0, crop_y]
            steps.append(f'scale=4096:-1[video_step_zero];[video_step_zero]crop={":".join(map(str, ret))}')
        if reverse:
            steps.append('reverse')
        return steps

    @decorator.timer
    @decorator.execute
    def combine(
        self,
        watermark_path='/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png',
        watermark_transparent=0.3,
        audio_path: Optional[str] = None,
        audio_defer: float = 0,
        fade_duration: float = 1,
        crop: str = '1080p',
        crop_y: int = 0,
        reverse: bool = False,
    ):
        """视频混合处理:
            - 添加logo并设置透明度
            - 添加音频并设置淡入淡出及过度时长
            - 视频剪切尺寸及y轴偏移量
            - 反转视频流

        Keyword Arguments:
            watermark_path {str} -- [logo文件路径]
            watermark_transparent {float} -- [logo透明度 范围: 0-1] (default: {0.3})
            audio_path {str} -- [背景音频文件路径] (default: {None})
            audio_defer {int/float} -- [背景音频文件截取处 单位:秒] (default: {0})
            fade_duration {int/float} -- [淡入淡出过度时长 单位:秒] (default: {1})
            crop {str} -- [视频剪切尺寸 可选: 1080p,4k] (default: {'1080p'})
            crop_y {int} -- [视频剪切y轴偏移量] (default: {0})
            reverse {bool} -- [是否反转视频流] (default: {False})
        """
        command = self._FFMPEG_PREFIX.copy()
        # 源视频必须是第一个输入: 滤镜里 [0:v] 指的就是它, logo/音频依次是 1、2
        command.extend(['-i', self.path])

        # 额外输入的顺序决定滤镜里的流编号: 0=源视频, 1=logo, 2=音频
        watermark_filters: list[str] = []
        if watermark_path:
            command.extend(['-i', watermark_path])
            watermark_filters = self._watermark_filters(watermark_transparent)

        audio_filters: list[str] = []
        if audio_path is not None:
            command.extend(['-ss', str(audio_defer), '-t', str(float(self.duration)), '-i', audio_path])
            audio_filters = self._audio_filters(fade_duration, input_index=2 if watermark_filters else 1)

        video_steps = self._video_filters(crop, crop_y, reverse)
        filter_complex: list[str] = []
        if video_steps:
            # 视频链必须排在 logo 之前, 且 logo 的输入要换成裁剪后的标签
            filter_complex.append('[0:v]' + ','.join(video_steps) + '[video_step_one]')
            if watermark_filters:
                watermark_filters[0] = '[1:v][video_step_one]scale2ref=h=ow/mdar:w=iw/9[logo][video]'
        filter_complex.extend(watermark_filters)
        filter_complex.extend(audio_filters)

        if filter_complex:
            command.extend(['-filter_complex', ';'.join(filter_complex)])

        new_file_path = self.get_output_path(suffix='combine')
        command.extend(
            [
                # 视频质量 1-51, crf=8 接近视觉无损; 之后四项是 BT.2020 色彩标记
                '-x265-params',
                'crf=8',
                '-color_primaries',
                '9',
                '-colorspace',
                '9',
                '-color_trc',
                '14',
                '-color_range',
                '2',
                new_file_path,
            ]
        )
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def delete_voice(self):
        """silence audio."""
        new_file_path = self.get_output_path(suffix='delete_voice')
        command = self._FFMPEG_PREFIX + ['-i', self.path, '-an', '-c:v', 'copy', new_file_path]
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def trim(self, trim_time=(), suffix_number: int = 1):
        """截取视频指定某一段时间

        Keyword Arguments:
            time {tuple} -- {截取时间段} (default: {()})
                e.g.: ("00:26:56", "00:28:36")
            suffix_number {number} -- 1 (default: {1})

        Returns:
            bool -- [description]
        """
        if not isinstance(trim_time, (tuple, list)) or len(trim_time) != 2:
            raise ValueError('参数[time]必须为长度为2的tuple或list')
        ss, to = trim_time
        new_file_path = self.create_file_path(self.path, suffix='trim', suffix_number=suffix_number)
        command = (
            f'{" ".join(self._FFMPEG_PREFIX)} -ss {ss} -to {to} -accurate_seek '
            f'-i {self.path} -c:v copy -c:a copy {new_file_path}'
        )
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def compress(self, ext: str = 'mp4', resolution=None, fps=None):
        """Push the compression lever further by increasing the CRF value — add, say, 4 or 6,
        since a reasonable range for H.265 may be 24 to 30. Note that lower CRF values correspond
        to higher bitrates, and hence produce higher quality videos.

        :param resolution: 目标分辨率, 接受 VideoResolution 成员 / 枚举名 (HD/FHD/UHD...) / '1920x1080';
            None 时取 CONFIG.COMPRESS_RESOLUTION 兜底值
        :param fps: 输出帧率, None 时取 CONFIG.COMPRESS_FPS 兜底值

        -c:v: libx264, libx265, qtrle, libvpx, libvpx-vp9
        hardware acceleration:
        -c:v: hevc_videotoolbox, h264_videotoolbox
        """
        # 兜底值来自 CONFIG (可 env/.env 覆盖), CLI 显式传入时以 CLI 为准
        resolution = VideoResolution.parse(resolution if resolution is not None else CONFIG.COMPRESS_RESOLUTION)
        fps = CONFIG.COMPRESS_FPS if fps is None else int(fps)

        command = self._ffmpeg_prefix + [
            '-progress',
            'pipe:1',
            '-nostats',
            # '-hwaccel', 'auto',
            '-i',
            self.path,
            # # To scale to half size
            # '-vf', "scale=trunc(iw/4)*2:trunc(ih/4)*2",
            # # To scale to One-third size
            # '-vf', "scale=trunc(iw/6)*2:trunc(ih/6)*2",
        ]

        # Change resolution if needed
        width, height = self.resolution
        if resolution.width >= width:
            pass
        elif resolution.pixels >= (width * height):
            pass
        else:
            # 用 scale 保持原始长宽比, 而非 -s 强制目标 WxH (会拉伸/裁剪, 破坏竖屏等非 16:9 视频)
            # force_original_aspect_ratio=decrease 只缩小不放大, 第二个 scale 保证宽高为偶数 (x265 硬性要求)
            command.extend(
                [
                    '-vf',
                    f'scale={resolution.width}:{resolution.height}:'
                    'force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2',
                ]
            )

        suffix, vcodec, preset = 'compress', 'libx265', 'slow'
        new_file_path = self.create_file_path(self.path, suffix=f'[{suffix}.{vcodec}.{preset}]', ext=ext)

        command.extend(
            [
                # Change FPS
                '-r',
                str(fps),
                # More faster, but more bigger size.
                # '-vcodec', 'libx264',
                # More smaller size, but more time, more CPU usage. Option parameter crf 0-51, 0 is lossless, 23 is default, and 51 is worst quality possible.
                # -preset: ultrafast, superfast, veryfast, faster, fast, medium(default), slow, slower, veryslow, placebo
                # '-vcodec', vcodec,
                '-c:v',
                vcodec,
                '-preset',
                preset,
                # Use RGBA pixel format to keep transparency
                # '-pix_fmt', 'rgba',
                # 10-bit 提升压缩效率 (~5-10% 同视觉质量下体积减少)
                # Ensure that the output video has a preview image
                '-tag:v',
                'hvc1',
                '-pix_fmt',
                'yuv420p10le',
                # x265 调优参数: 自适应量化 + 关闭 SAO 滤波器
                '-x265-params',
                'aq-mode=3:no-sao=1',
                # 音频: AAC 96k 44100Hz (平衡质量与体积)
                '-c:a',
                'aac',
                '-b:a',
                '96k',
                '-ar',
                '44100',
                # crf 0-51, 0 is lossless, 23 is default, and 51 is worst quality possible
                # '-crf', '24',
                # '-avoid_negative_ts', 'make_zero',
                new_file_path,
            ]
        )

        # videotoolbox
        # More faster, more smaller size.
        # command = self._FFMPEG_PREFIX + [
        #     "-i", self.path,
        #     "-c:a", "copy",
        #     "-c:v",
        #     "h264_videotoolbox",
        #     "-q:v",
        #     "50",
        #     new_file_path,
        # ]

        # videotoolbox: H.265 / HEVC (High Efficiency Video Coding), hevc_videotoolbox isn't as good as libx265, \
        # but it is fast
        # More faster, more smaller size.
        # * -hwaccel videotoolbox: Use VideoToolbox hardware acceleration.
        # Use -b:v to control quality. -crf is only for libx264, libx265, libvpx, and libvpx-vp9. It will be ignored by other encoders. It will also ignore -preset.
        # * -q:v 50: Constant quality mode (VBR). Lower values mean better quality, The value should be 1-100, \
        # the higher the number, the better the quality. 65 seems to be acceptable.
        # command = self._FFMPEG_PREFIX + [
        #     "-i", self.path,
        #     "-vcodec", "hevc_videotoolbox", "-tag:v", "hvc1",
        #     "-q:v", "65",
        #     new_file_path,
        # ]
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def decode(self, ext: str = 'mp4'):
        """解码视频"""
        new_file_path = self.dirname + '/' + self.title + '_decode_.' + ext
        command = self._FFMPEG_PREFIX + [
            '-i',
            self.path,
            # 线程(待验证)
            # '-threads', '4',
            # '-avoid_negative_ts', '1',
            new_file_path,
        ]
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def convert_format(self, ext: str = 'mp4', **kwargs):
        """转换视频格式"""
        new_file_path = self.create_file_path(self.path, suffix=f'[convert.{ext}]', ext=ext)
        vcodec = 'copy'
        vcodec = 'libx265'
        command = self._FFMPEG_PREFIX + [
            '-i',
            self.path,
            # '-map', '0', '-c', 'copy',
            '-c:v',
            vcodec,
            '-c:a',
            'copy',
            '-tag:v',
            'hvc1',
            # '-avoid_negative_ts', '1',
            new_file_path,
        ]
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def scale(self, width: int = 1920, height: int = 1080, **kwargs):
        """Scale video resolution."""
        new_file_path = self.create_file_path(self.path, suffix=f'[scale.{width}x{height}]', ext='mp4')
        command = self._FFMPEG_PREFIX + [
            '-i',
            self.path,
            '-vf',
            f'scale={width}:{height}',
            '-c:v',
            'libx265',
            '-tag:v',
            'hvc1',
            new_file_path,
        ]
        return self, command, new_file_path
