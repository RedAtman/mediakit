from functools import cached_property
import json
import logging
import os
import sys
import threading
import time
from typing import List, Optional, Self, Type

from config import CONFIG
from src import models
from utils import exceptions
from utils.command import CommandExecutor, ProgressMonitor
from utils.file import calculate_md5
from utils.media import guess
from utils.process.parser import FfmpegCurrentFrameStdoutParser
from utils.progress import BaseProgress, MediaStateProgress, StdoutProgress


logger = logging.getLogger()

__all__ = [
    "BaseMedia",
]


class BaseMedia:
    """Base media class."""

    _INCLUDE_TYPE = [
        "image",
        "audio",
        "video",
    ]
    _LOG_LEVEL = CONFIG.LOG_LEVEL.lower()
    _LOCK = threading.Lock()

    _CPULIMIT_BIN = os.path.join(CONFIG.CPULIMIT_BIN_DIR, "cpulimit")
    _CPULIMIT_PREFIX = []
    if CONFIG.CPULIMIT_LIMIT:
        _CPULIMIT_PREFIX = [
            _CPULIMIT_BIN,
            "--limit",
            str(CONFIG.CPULIMIT_LIMIT),
            "--lazy",
            # "--",
        ]

    _FFMPEG_BIN = os.path.join(CONFIG.FFMPEG_BIN_DIR, "ffmpeg")
    _FFPROBE_BIN = os.path.join(CONFIG.FFMPEG_BIN_DIR, "ffprobe")
    if not os.path.exists(_FFMPEG_BIN):
        raise FileNotFoundError(f"File not found at path: {_FFMPEG_BIN}")
    if not os.path.exists(_FFPROBE_BIN):
        raise FileNotFoundError(f"File not found at path: {_FFPROBE_BIN}")
    _FFMPEG_PREFIX: list[str] = _CPULIMIT_PREFIX + [
        _FFMPEG_BIN,
        "-y",
        "-loglevel",
        _LOG_LEVEL,
        # '-i', self.path,
        # "-threads", "16",
        # "-threads:v",
    ]
    _FFPROBE_PREFIX: list[str] = [
        _FFPROBE_BIN,
        "-v",
        _LOG_LEVEL,
    ]
    logger.debug(("_FFMPEG_PREFIX", _FFMPEG_PREFIX))
    # logger.debug("FFMPEG: %s", " ".join(_FFMPEG_PREFIX))

    # TODO: Type[super]?
    _SUBCLASS_MAPPER: dict[str, Type[Self]] = {}
    _MEDIA_CLS: Type[models.Media] = models.Media

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._SUBCLASS_MAPPER[cls.__name__.lower()] = cls

    def __init__(self, path: str):
        super().__init__()
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found at path: {path}")
        if not os.path.isfile(path):
            raise exceptions.NotMediaException(101, f"Path is not a file: {path}")
        if guess(path) not in self._INCLUDE_TYPE:
            raise exceptions.NotMediaException(101, f"File is not media file: {path}")
        logger.debug("BaseMedia: %s", path)
        self.path: str = path
        self.dirname, self.title, self.ext = self.get_file_info(path)
        self.model: models.Media = self._MEDIA_CLS.get_or_create(
            md5=self.md5,
            title=self.title + "." + self.ext,
            dirname=self.dirname,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.path})"

    @property
    def _ffmpeg_prefix(self) -> List[str]:
        _CPULIMIT_PREFIX = []
        logger.info("CPULIMIT: %s", CONFIG.CPULIMIT_LIMIT)
        if CONFIG.CPULIMIT_LIMIT:
            _CPULIMIT_PREFIX = [
                self._CPULIMIT_BIN,
                "--limit",
                str(CONFIG.CPULIMIT_LIMIT),
                "--lazy",
            ]
        return _CPULIMIT_PREFIX + self._FFMPEG_PREFIX

    @cached_property
    def md5(self):
        """Get media file md5.

        Returns:
            [str] -- [md5]
        """
        return calculate_md5(self.path)

    @property
    def progress_list(self) -> List[BaseProgress]:
        return [
            StdoutProgress(total=self.frames_count, title=self.path, fmt=StdoutProgress.FULL),
            MediaStateProgress(total=self.frames_count, model=self.model),
        ]

    @property
    def monitor(self):
        return ProgressMonitor(FfmpegCurrentFrameStdoutParser, self.progress_list)

    @cached_property
    def frames_count(self):
        """Get media file frames count.

        e.g.:
            # More speed and if nb_frames is reliable enough, simplify as: but nb_frames is not always reliable.
            # Problem: Often returns N/A, not reliable.
            ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames \
                -of default=nokey=1:noprint_wrappers=1 input.mp4
            ffprobe -select_streams v -show_streams input.mp4 2>/dev/null | grep nb_frames | sed -e 's/nb_frames=//'
            ffprobe -v error -select_streams v -show_streams input.mp4 | grep nb_frames | sed -e s/nb_frames=//
            ffprobe -v error -show_streams -hide_banner input.mp4 | grep "nb_frames" | sed -e s/nb_frames=//
            ffprobe -v error -show_streams -hide_banner input.mp4 | grep "nb_frames" | head -n1 | cut -d"=" -f2

            # More reliable. but slower.
            ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames \
                -of default=nokey=1:noprint_wrappers=1 input.mp4
            ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets \
                -of csv=p=0 input.mp4

            # TODO: Unverified.
            ffmpeg -i input.mp4 -vcodec copy -acodec copy -f null /dev/null 2>&1 | grep 'frame=' | cut -f 2 -d ' '
            ffprobe -i input.mp4 -print_format json -loglevel fatal -show_streams -count_frames -select_streams v
            ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate \
                -of default=noprint_wrappers=1:nokey=1 input.mp4
            ffmpeg -i input.mp4 -map 0:v:0 -c copy -f null -

        """
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
            logger.warning(f"Cannot get frames count: {self.path}, set to {default_frames_count}.")
            return default_frames_count

    @cached_property
    def metadata(self):
        return self.get_metadata(self.path)

    @classmethod
    def get_metadata(cls, path: str):
        """Get media file metadata.

        Arguments:
            path {[str]} -- [Media file path]

        Returns:
            [type] -- [description]
        """
        command = [
            cls._FFPROBE_BIN,
            "-v",
            "quiet",
            "-show_format",
            "-show_streams",
            "-print_format",
            "json",
            path.strip(),
        ]
        command = f"{cls._FFPROBE_BIN} -v quiet -show_format -show_streams -print_format json {path.strip()}"
        metadata = CommandExecutor.run(command)
        try:
            return json.loads(metadata)
        except Exception as err:
            raise TypeError(f"Not a json string: {metadata}") from err

    @cached_property
    def width_height(self):
        """Get media file width and height. Unit:pixel"""
        width, height = 0, 0
        _format = self.metadata.get("format")
        if _format and _format.get("width") and _format.get("height"):
            width, height = _format.get("width"), _format.get("height")
        else:
            for stream in self.metadata.get("streams"):
                if stream.get("width") and stream.get("height"):
                    width, height = stream.get("width"), stream.get("height")
                    break
        return width, height

    @cached_property
    def bitrate(self):
        """Get media file bitrate. Unit:kb/s"""
        bitrate = self.metadata.get("streams")[0].get("bit_rate") or self.metadata.get("format").get("bit_rate")
        return float(bitrate)

    @cached_property
    def duration(self):
        """Get media file duration. Unit:second"""
        # result = subprocess.run([
        #     "ffprobe", "-v", "error", "-show_entries",
        #     "format=duration", "-of",
        #     "default=noprint_wrappers=1:nokey=1", self.path],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.STDOUT)
        # return float(result.stdout)

        return self.metadata.get("streams")[0].get("duration")

    @staticmethod
    def get_file_info(path: str):
        """Get file info.: dirname, title, ext.

        Arguments:
            path {[str]} -- [File path]

        Returns:
            [tuple] -- [dirname, title, ext]
        """
        title, ext = os.path.splitext(os.path.basename(path))
        return os.path.dirname(path), title, ext[1:]

    @cached_property
    def output_path(self):
        """Media output path"""
        return self.get_output_path()

    def get_output_path(self, suffix=""):
        """媒体输出路径(代替 self.output_path)

        Keyword Arguments:
            suffix {str} -- [输出文件名后缀] (default: {''})

        Returns:
            [str] -- [媒体输出路径]
        """
        # suffix or caller function name
        suffix = suffix or sys._getframe().f_back.f_code.co_name
        return f'{self.dirname}/_{self.title}_{suffix}_{time.strftime("%Y%m%d%H%M%S", time.localtime())}.{self.ext}'

    @classmethod
    def create_file_path(
        cls,
        path: str,
        suffix: str = "",
        suffix_number: int = 1,
        ext: Optional[str] = None,
    ):
        """Create file path.

        Arguments:
            path {[type]} -- [description]

        Keyword Arguments:
            suffix {str} -- [description] (default: {'suffix'})
            suffix_number {number} -- [description] (default: {1})

        Returns:
            [type] -- [description]
                e.g.: /Users/nut/Downloads/RS/_trim/VIDEO_trim_1.mp4
        """
        dirname, title, _ext = cls.get_file_info(path)
        ext = ext or _ext
        suffix = suffix or sys._getframe().f_back.f_code.co_name
        dirname = os.path.join(dirname, "_" + suffix)
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

        with cls._LOCK:
            while True:
                file_path = os.path.join(dirname, f"{title}-{suffix}_{suffix_number}.{ext}")
                # file_path = os.path.join(dirname, f"{title}.{ext}")
                if not os.path.exists(file_path):
                    break
                suffix_number += 1
        return file_path
