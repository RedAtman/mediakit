from functools import cached_property, partial
import json
import logging
import os
import sys
import threading
import time
from typing import Optional, Self, Type

from config import CONFIG
from src import models
from utils import exceptions
from utils.command import CommandExecutor
from utils.media import guess
from utils.tools import calculate_md5


logger = logging.getLogger()

__all__ = [
    "BaseMedia",
]


class BaseMedia:
    """docstring for BaseMedia"""

    _INCLUDE_TYPE = [
        "image",
        "audio",
        "video",
    ]
    _LOG_LEVEL = CONFIG.LOG_LEVEL.lower()
    _LOCK = threading.Lock()
    _executor = partial(CommandExecutor)
    _FFMPEG_BIN = os.path.join(CONFIG.FFMPEG_BIN_DIR, "ffmpeg")
    _FFPROBE_BIN = os.path.join(CONFIG.FFMPEG_BIN_DIR, "ffprobe")
    if not os.path.exists(_FFMPEG_BIN):
        raise FileNotFoundError(f"File not found at path: {_FFMPEG_BIN}")
    if not os.path.exists(_FFPROBE_BIN):
        raise FileNotFoundError(f"File not found at path: {_FFPROBE_BIN}")
    # TODO: Type[super]?
    _SUBCLASS_MAPPER: dict[str, Type[Self]] = {}
    _FFMPEG_PREFIX: list[str] = [
        _FFMPEG_BIN,
        "-y",
        "-loglevel",
        _LOG_LEVEL,
        # '-i', self.path,
        # '-threads', '16',
    ]
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
        self.media: models.Media | None = self._MEDIA_CLS.get(md5=self.md5)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.path})"

    @cached_property
    def md5(self):
        """Get media file md5.

        Returns:
            [str] -- [md5]
        """
        return calculate_md5(self.path)

    @property
    def executor(self) -> CommandExecutor:
        try:
            frames_count = self.frames_count
            title = self.path
            return self._executor(total=frames_count, title=title)
        except Exception:
            return self._executor()

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
            result = CommandExecutor.execute(
                f'{self._FFPROBE_BIN} -v error -select_streams v -show_streams "{self.path}" | grep nb_frames | sed -e s/nb_frames=//'
            )
            return int(result)
        except ValueError:
            result = CommandExecutor.execute(
                f'{self._FFPROBE_BIN} -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=nokey=1:noprint_wrappers=1 "{self.path}"'
            )
            return int(result)
        except Exception as err:
            logger.exception(err)
            raise err

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
        metadata = CommandExecutor.execute(command)
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
        bitrate = self.metadata.get("streams")[0].get("bit_rate") or self.metadata.get(
            "format"
        ).get("bit_rate")
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
                file_path = os.path.join(
                    dirname, f"{title}-{suffix}_{suffix_number}.{ext}"
                )
                if not os.path.exists(file_path):
                    break
                suffix_number += 1
        return file_path
