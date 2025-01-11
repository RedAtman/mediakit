from dataclasses import dataclass
import functools
import logging
import time
from typing import Any, Dict, List, Optional, Set, Union

from base.media import BaseMedia
from src.mixins import whispers
from utils import decorator, translator
from utils.command import CommandExecutor

from .media import BaseMedia


logger = logging.getLogger()
__all__ = [
    "Video",
]


@dataclass
class Resolutions:
    QVGA: str = "320x240"
    QQVGA: str = "352x288"
    HVGA: str = "480x320"
    QHVGA: str = "480x360"
    WQVGA: str = "400x240"
    QWVGA: str = "480x320"
    VGA: str = "640x480"
    WVGA: str = "800x480"
    FWVGA: str = "854x480"
    SVGA: str = "800x600"
    WSVGA: str = "1024x600"
    WSXGA: str = "1280x720"
    WXGA: str = "1280x800"
    SXGA: str = "1280x1024"
    WSXGA_plus: str = "1400x1050"
    WXGA_plus: str = "1440x900"
    SXGA_plus: str = "1600x1200"
    HDTV_720p: str = "1280x720"
    HDTV_standard: str = "1920x1080"


class Video(
    BaseMedia,
    # whispers.MixinMediaWhisper,
    whispers.MixinMediaFasterWhisper,
    # whispers.MixinMediaWhisperCPP,
):
    _INCLUDE_TYPE = [
        "video",
    ]

    def __init__(
        self,
        *args,
        artist: str = "",
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
        meta_key_list = [
            "title",
            "artist",
            "album_artist",
            "category",
            "camera",
            "lens",
            "keywords",
        ]
        order_metadata: List[str] = []
        for key in meta_key_list:
            meta: Union[str, list] = getattr(self, key)
            if not meta:
                continue

            if isinstance(meta, str):
                order_metadata.extend(["-metadata", str(key) + "=" + meta])
                self.keywords_list.add(meta)
            if isinstance(meta, list):
                order_metadata.extend(["-metadata", str(key) + "=" + ",".join(meta)])
                self.keywords_list.update(meta)
            # 若是dict 则拼接values
            if isinstance(meta, dict):

                def concat(a, b):
                    logger.info(("concat", type(a), type(b)))
                    a.extend(b)
                    return a

                meta_concat = functools.reduce(concat, list(meta.values()))

                order_metadata.extend(["-metadata", str(key) + "=" + ",".join(meta_concat)])
                self.keywords_list.update(meta_concat)

        keywords_en_list = translator.Translator.translate(self.keywords_list)
        self.keywords_list.update(keywords_en_list)
        self.keywords_list = {i.strip() for i in self.keywords_list}

        order_metadata.extend(["-metadata", "keywords" + "=" + ",".join(self.keywords_list)])

        return order_metadata

    @decorator.timer
    def save_metadata(self):
        """Save metadata to file(txt)."""
        return [
            "-f",
            "ffmetadata",
            self.dirname + "/" + self.title + "_metadate" + ".txt",
        ]

    @decorator.timer
    def set_metadata(self):
        """Set metadata to file."""
        return self.order_metadata.extend(
            [
                "-c:a",
                "copy",
                "-c:v",
                "copy",
                self.get_output_path(suffix="set_metadata"),
            ]
        )

    @property
    def fps(self):
        fps: Dict[str, Any] = self._fps()
        assert isinstance(fps, str), f"fps must be str, but got: {type(fps)}: {fps}"
        assert fps.isdigit(), f"fps must be digit, but got: {type(fps)}: {fps}"
        return float(fps)

    @decorator.timer
    def _fps(self):
        """Get video fps."""
        command = [
            self._FFPROBE_BIN,
            "-v",
            "error",
            "-select_streams",
            "v",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            "-show_entries",
            "stream=r_frame_rate",
            self.path,
            "|",
            "bc",
            # "-l",
        ]
        return CommandExecutor.run(command, mode="pipe")

    @decorator.timer
    @decorator.execute
    def reverse(self):
        """Reverse video stream."""
        new_file_path = self.get_output_path(suffix="reverse")
        command = self._FFMPEG_PREFIX + [
            "-i",
            self.path,
            "-vf",
            "reverse",
            # '-aspect', '3:2',
            "-aspect",
            "16:9",
            "-c:v",
            "libx265",
            "-pix_fmt",
            "yuv420p10le",
            # "-threads",
            # "0",
            "-tag:v",
            "hvc1",
            "-x265-params",
            "crf=22",
            "-an",
            # '-metadata', 'creation_time="2020-08-11T21:30:32"',
            "-metadata",
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

    @decorator.timer
    @decorator.execute
    def combine(
        self,
        watermark_path="/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png",
        watermark_transparent=0.3,
        audio_path: Optional[str] = None,
        audio_defer: float = 0,
        fade_duration: float = 1,
        crop: str = "1080p",
        crop_y: int = 0,
        reverse: bool = False,
    ):
        """视频混合处理:
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
        """

        command = self._FFMPEG_PREFIX.copy()
        filter_complex: List[str] = []

        if watermark_path:
            command.extend(
                [
                    "-i",
                    watermark_path,
                ]
            )
            filter_complex.extend(
                [
                    """atempo=2,[1:v][0:v]scale2ref=h=ow/mdar:w=iw/9[logo][video]""",
                    """[logo]format=argb,colorchannelmixer=aa=""" + str(watermark_transparent) + "[logo]",
                    """[video][logo] overlay=(main_w-w)*0.7:(main_h-h)*0.7""",
                ]
            )
        if audio_path is not None:
            command.extend(
                [
                    "-ss",
                    str(audio_defer),
                    "-t",
                    str(float(self.duration)),
                    "-i",
                    audio_path,
                ]
            )
            filter_complex.extend(
                [
                    # '[0:a]aeval=0:c=same[audio]',
                    "[2:a]afade=t=in:st=0:d="
                    + str(fade_duration)
                    + ",afade=t=out:st="
                    + str(float(self.duration) - 1)
                    + ":d="
                    + str(fade_duration)
                    + ",volume=12dB",
                    # '[audio][music]amix=inputs=2:duration=shortest:dropout_transition=2',
                ]
            )

        # vf = []
        video_step_one: List[str] = []

        resolution_mapper = {
            "1080p": [1920, 1080],
            "4k": [4096, 2160],
            # '4k': '4096:2304',
            # '4k': '4096:2736'
        }
        resolution = resolution_mapper.get(crop)
        if resolution:
            # 画面裁剪 crop=width:height 或 # crop=width:-1
            # 画面裁剪 crop=width:height:x:y width:height表示裁剪后的尺寸
            # x:y表示裁剪区域的左上角坐标
            # '-vf', 'crop=1920:1080:0:0',
            # '-vf', 'crop=4096:2160:0:288',
            # vf.extend(['crop=1920:1080:0:200'])
            xy = [0, crop_y]
            ret = resolution + xy

            # video_step_one.append(
            #     'scale=' + '4096:-1' + '[video_step_zero];[video_step_zero]' + 'crop=' + ':'.join(map(lambda x: str(x), ret)))
            video_step_one.append(f'scale=4096:-1[video_step_zero];[video_step_zero]crop={":".join(map(str, ret))}')

        if reverse:
            video_step_one.append("reverse")

        if video_step_one:
            # print('filter_complex', filter_complex)
            filter_complex[0] = "[1:v][video_step_one]scale2ref=h=ow/mdar:w=iw/9[logo][video]"
            filter_complex.insert(0, "[0:v]" + ",".join(video_step_one) + "[video_step_one]")

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

        command.extend(
            [
                "-filter_complex",
                ";".join(filter_complex),
                # 时长取最短的media
                # '-shortest',
            ]
        )

        new_file_path = self.get_output_path(suffix="combine")
        command.extend(
            [
                # 长宽比约束
                # '-aspect', '16:9',
                # '-pix_fmt', 'yuv420p10le',
                # '-threads', '0',
                # '-tag:v', 'hvc1',
                "-x265-params",
                # 视频质量范围（1-51） 8为Ultra Hight 22为Low
                "crf=8",
                # 禁掉源文件中的音频
                # '-an',
                # '-metadata','creation_time="2020-08-11T21:30:32"',
                # 颜色
                # 最高参数 似乎一样
                # '-color_primaries', '22',
                # '-colorspace', '11',
                # '-color_trc', '18',
                "-color_primaries",
                "9",
                "-colorspace",
                "9",
                "-color_trc",
                "14",
                "-color_range",
                "2",
                # 视频码率
                # '-b:v', '4000k',
                # 视频速度调整
                # '-vf', "setpts=0.5*PTS",
                # 对音频速度调整限制在0.5 到 2.0 之间（即半速或倍速）
                # '-af', "atempo=2.0",
                new_file_path,
            ]
        )
        return self, command, new_file_path

    @decorator.timer
    def images_to_video(self, images_path: str, image_format: str, bit_rate: str = "5000k"):
        create_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        new_file_path = f"{images_path}/output_{bit_rate}_1920_{create_time}.mp4"
        command = self._FFMPEG_PREFIX + [
            # 关闭每帧都提醒是否overwrite
            "-pattern_type",
            "glob",
            # 设置帧率
            "-r",
            "24",
            # 设置images文件路径,
            "-i",
            images_path + "/*." + image_format,
            # 码率
            # '-b:v', bit_rate,
            # 线程(待验证)
            # "-threads",
            # "4",
            # 画面缩放比率
            "-vf",
            "scale=1920:-1",
            # 对video类型文件设置编码类型
            # '-c:v', 'libx264',
            # '-c:v', 'libx265',
            # 时长取最短的media
            # '-shortest',
            new_file_path,
        ]
        CommandExecutor.run(command)
        return self, command, new_file_path

    @decorator.timer
    def delete_voice(self):
        """silence audio."""
        return [
            "-an",
            "-c:v",
            "copy",
            self.get_output_path(suffix="delete_voice"),
        ]

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
        if not isinstance(trim_time, (tuple, list)) and len(trim_time) != 2:
            raise ValueError("参数[time]必须为长度为2的tuple或list")
        ss, to = trim_time
        new_file_path = self.create_file_path(self.path, suffix="trim", suffix_number=suffix_number)
        command = self._FFMPEG_PREFIX + [
            # 截取时间
            "-ss",
            ss,
            "-to",
            to,
            # 使用copy后 避免太过于精确切割而丢失帧
            "-accurate_seek",
            "-i",
            self.path,
            # 线程(设置为4效率最高, 但通用性待验证)
            # '-threads', '4',
            # 对video类型文件设置编码类型
            # 注意：copy会带来前面一段时间丢帧问题并且无预览图
            # '-c', 'copy',
            # '-c:a', 'copy',
            # '-c:v', 'copy',
            # 若voice copy失败
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            # '-acodec', 'aac',
            # '-avoid_negative_ts', '1',
            new_file_path,
        ]
        command = f'{" ".join(self._FFMPEG_PREFIX)} -ss {ss} -to {to} -accurate_seek \
            -i {self.path} -c:v copy -c:a copy {new_file_path}'
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def compress(self, ext: str = "mp4", resolution: str = Resolutions.HDTV_720p, fps: int = 24):
        """Push the compression lever further by increasing the CRF value — add, say, 4 or 6,
        since a reasonable range for H.265 may be 24 to 30. Note that lower CRF values correspond
        to higher bitrates, and hence produce higher quality videos.

        -c:v: libx264, libx265, qtrle, libvpx, libvpx-vp9
        """
        suffix, vcodec, preset = "compress", "libx265", "medium"
        new_file_path = self.create_file_path(self.path, suffix=f"[{suffix}.{vcodec}.{preset}]", ext=ext)

        # More smaller size, but more time, more CPU usage.
        command = self._ffmpeg_prefix + [
            # '-hwaccel', 'auto',
            "-i",
            self.path,
            # # To scale to half size
            # '-vf', "scale=trunc(iw/4)*2:trunc(ih/4)*2",
            # # To scale to One-third size
            # '-vf', "scale=trunc(iw/6)*2:trunc(ih/6)*2",
            # Change resolution
            # "-s",
            # "",
            # Change FPS
            "-r",
            str(fps),
            # More faster, but more bigger size.
            # '-vcodec', 'libx264',
            # More smaller size, but more time, more CPU usage. Option parameter crf 0-51, 0 is lossless, 23 is default, and 51 is worst quality possible.
            # -preset: ultrafast, superfast, veryfast, faster, fast, medium(default), slow, slower, veryslow, placebo
            # '-vcodec', vcodec,
            "-c:v",
            vcodec,
            "-preset",
            preset,
            # Use RGBA pixel format to keep transparency
            # '-pix_fmt', 'rgba',
            # Ensure that the output video has a preview image
            "-tag:v",
            "hvc1",
            # crf 0-51, 0 is lossless, 23 is default, and 51 is worst quality possible
            # '-crf', '24',
            # '-avoid_negative_ts', 'make_zero',
            new_file_path,
        ]

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

    # @decorator.timer
    # def compress(self):
    #     width, height = self.width_height
    #     bitrate = 3200000 / 1280 / 720
    #     bitrate = bitrate * width * height
    #     # logger.warning('bitrate: %s, self.bitrate: %s', bitrate, self.bitrate)
    #     if bitrate >= self.bitrate:
    #         logger.warning("bitrate: %s, self.bitrate: %s", bitrate, self.bitrate)
    #         bitrate = self.bitrate
    #         # raise ValueError(f'output bit_rate({bitrate}) must < origin bit_rate({self.bitrate})')
    #     return self._compress(self.path, width=width, height=height, bitrate=bitrate)

    @classmethod
    def _compress(
        cls,
        path: str,
        width: int = 1280,
        height: int = 720,
        # bitrate=1600000,
        bitrate: float = 3200000.00,
    ):
        """压缩视频

        Keyword Arguments:
            width {int} -- [压缩分辨率宽度 单位px] (default: {1280})
            height {int} -- [压缩分辨率高度 单位px] (default: {720})
            bitrate {int} -- [压缩码率 单位kb/s] (default: {3200000})

        Returns:
            [type] -- [description]
        """
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

        new_file_path = cls.create_file_path(path, suffix="compress")
        command = cls._FFMPEG_PREFIX + [
            "-i",
            path,
            "-s",
            str(width) + "x" + str(height),
            "-aspect",
            str(width) + ":" + str(height),
            # "-threads",
            # "0",
            "-c:v",
            "hevc_videotoolbox",
            "-r",
            "24.00",
            "-pix_fmt",
            "yuv420p",
            "-b:v",
            str(bitrate),
            "-maxrate",
            str(bitrate + 200000),
            "-bufsize",
            "4M",
            "-allow_sw",
            "1",
            "-profile:v",
            "main",
            "-vtag",
            "hvc1",
            "-c:a:0",
            "aac",
            "-ac:a:0",
            "2",
            "-ar:a:0",
            "32000",
            "-b:a:0",
            "128k",
            # '-b:a:0', '256k',
            "-strict",
            "-2",
            "-sn",
            # ffmpeg can automatically determine the appropriate format
            # from the output file name, so most users can omit the -f option.
            "-f",
            "mp4",
            "-map",
            "0:0",
            "-map",
            "0:1?",
            "-map_chapters",
            "0",
            "-max_muxing_queue_size",
            "40000",
            "-map_metadata",
            "0",
            new_file_path,
        ]
        # logger.warning(
        #     'Thread: %s, Parent Process: %s, Function: %s, command: %s',
        #     threading.current_thread().name, os.getpid(),
        #     sys._getframe().f_code.co_name,
        #     command,
        # )
        CommandExecutor.run(command)
        return cls, command, new_file_path

    @decorator.timer
    @decorator.execute
    def decode(self, ext: str = "mp4"):
        """解码视频"""
        new_file_path = self.dirname + "/" + self.title + "_decode_." + ext
        command = self._FFMPEG_PREFIX + [
            "-i",
            self.path,
            # 线程(待验证)
            # '-threads', '4',
            # '-avoid_negative_ts', '1',
            new_file_path,
        ]
        return self, command, new_file_path

    def concat(self):
        return "ffmpeg -f concat -i concat.txt -c copy concat.mov"

    @decorator.timer
    @decorator.execute
    def convert_format(self, ext: str = "mp4", **kwargs):
        """转换视频格式"""
        new_file_path = self.create_file_path(self.path, suffix=f"[convert.{ext}]", ext=ext)
        vcodec = "copy"
        vcodec = "libx265"
        command = self._FFMPEG_PREFIX + [
            "-i",
            self.path,
            # '-map', '0', '-c', 'copy',
            "-c:v",
            vcodec,
            "-c:a",
            "copy",
            "-tag:v",
            "hvc1",
            # '-avoid_negative_ts', '1',
            new_file_path,
        ]
        return self, command, new_file_path

    @decorator.timer
    @decorator.execute
    def scale(self, width: int = 1920, height: int = 1080, **kwargs):
        """Scale video resolution."""
        new_file_path = self.create_file_path(self.path, suffix=f"[scale.{width}x{height}]", ext="mp4")
        command = self._FFMPEG_PREFIX + [
            "-i",
            self.path,
            "-vf",
            f"scale={width}:{height}",
            "-c:v",
            "libx265",
            "-tag:v",
            "hvc1",
            new_file_path,
        ]
        return self, command, new_file_path
