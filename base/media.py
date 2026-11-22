from functools import cached_property
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import threading
import time
from typing import List, Optional, Type

from config import CONFIG
from src import models
from src.progress import MediaStateProgress
from utils import exceptions
from utils.command import CommandExecutor, ProgressMonitor
from utils.file import calculate_md5
from utils.media import MEDIA_CATEGORIES, guess
from utils.process.parser import FfmpegCurrentFrameStdoutParser
from utils.progress import BaseProgress, TqdmProgress

logger = logging.getLogger()

__all__ = ['BaseMedia']


class BaseMedia:
    """Base media class."""

    _INCLUDE_TYPE = MEDIA_CATEGORIES
    _LOG_LEVEL = CONFIG.LOG_LEVEL.lower()
    _LOCK = threading.Lock()
    # APFS/HFS+ 和 Linux 的单个路径分量上限都是 255 字节, 不是 255 个字符
    NAME_MAX = 255

    _FFMPEG_BIN = (
        os.path.join(CONFIG.FFMPEG_BIN_DIR, 'ffmpeg') if CONFIG.FFMPEG_BIN_DIR else (shutil.which('ffmpeg') or 'ffmpeg')
    )
    _FFPROBE_BIN = (
        os.path.join(CONFIG.FFMPEG_BIN_DIR, 'ffprobe')
        if CONFIG.FFMPEG_BIN_DIR
        else (shutil.which('ffprobe') or 'ffprobe')
    )
    logger.debug('_FFPROBE_BIN: %s', _FFPROBE_BIN)

    _FFMPEG_PREFIX: list[str] = [
        _FFMPEG_BIN,
        '-y',
        '-loglevel',
        _LOG_LEVEL,
        # '-i', self.path,
        # "-threads", "16",
        # "-threads:v",
    ]
    _FFPROBE_PREFIX: list[str] = [_FFPROBE_BIN, '-v', _LOG_LEVEL]
    # logger.debug(("_FFMPEG_PREFIX", _FFMPEG_PREFIX))
    # logger.debug("FFMPEG: %s", " ".join(_FFMPEG_PREFIX))

    # TODO: Type[super]?
    _MEDIA_CLS: Type[models.Media] = models.Media

    @classmethod
    def reject_reason(cls, path: str) -> str | None:
        """Why path is not processable media, or None when it is.

        Single source of truth for the media filter: __init__ rejects on it, folder
        scans skip on it. One copy means the skip list and the raised exception can
        not drift apart.
        """
        if not os.path.isfile(path):
            return f'Path is not a file: {path}'
        if guess(path) not in cls._INCLUDE_TYPE:
            return f'File is not media file: {path}'
        return None

    def __init__(self, path: str):
        super().__init__()
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found at path: {path}')
        reason = self.reject_reason(path)
        if reason is not None:
            raise exceptions.NotMediaException(101, reason)
        logger.info('BaseMedia: %s', path)
        self.path: str = Path(path).absolute().as_posix()
        self.dirname, self.title, self.ext = self.get_file_info(path)
        self.model: models.Media = self._MEDIA_CLS.get_or_create(
            md5=self.md5, title=os.path.basename(path), dirname=self.dirname
        )

    def __repr__(self):
        return f'{self.__class__.__name__}({self.path})'

    @property
    def _ffmpeg_prefix(self) -> List[str]:
        return self._FFMPEG_PREFIX

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
            TqdmProgress(total=self.frames_count, title=self.path),
            MediaStateProgress(total=self.frames_count, model=self.model),
        ]

    @property
    def monitor(self):
        return ProgressMonitor(FfmpegCurrentFrameStdoutParser, self.progress_list)

    @cached_property
    def frames_count(self):
        """Number of frames. Only available for video media."""
        raise NotImplementedError(f'{type(self).__name__} does not support frames_count. Use a Video instance.')

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
        # 必须用列表, 不能拼成 shell 字符串: 文件名里的 & ( ) ' 空格会被 shell
        # 当成语法, 导致 ffprobe 以 127/解析错误失败 (见 has_decodable_audio)
        command = [
            cls._FFPROBE_BIN,
            '-v',
            'quiet',
            '-show_format',
            '-show_streams',
            '-print_format',
            'json',
            path.strip(),
        ]
        metadata = CommandExecutor.run(command)
        try:
            return json.loads(metadata)
        except Exception as err:
            raise TypeError(f'Not a json string: {metadata}') from err

    @cached_property
    def width_height(self):
        raise NotImplementedError(f'{type(self).__name__} does not support width_height. Use a Video instance.')

    @cached_property
    def bitrate(self):
        raise NotImplementedError(f'{type(self).__name__} does not support bitrate. Use a Video instance.')

    @cached_property
    def duration(self):
        raise NotImplementedError(f'{type(self).__name__} does not support duration. Use a Video instance.')

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

    def get_output_path(self, suffix=''):
        """媒体输出路径(代替 self.output_path)

        Keyword Arguments:
            suffix {str} -- [输出文件名后缀] (default: {''})

        Returns:
            [str] -- [媒体输出路径]
        """
        # suffix or caller function name
        suffix = suffix or sys._getframe().f_back.f_code.co_name
        tail = f'_{suffix}_{time.strftime("%Y%m%d%H%M%S", time.localtime())}.{self.ext}'
        return os.path.join(self.dirname, self.fit_filename(f'_{self.title}', tail))

    @staticmethod
    def fit_filename(title: str, tail: str) -> str:
        """拼 title + tail, 按字节把 title 截到不超过单个路径分量上限.

        素材名本身接近 255 字节时, 再追加 `-[compress.libx265.slow]_1` 会让 ffmpeg
        以 ENAMETOOLONG 退出 (外层只看到 exit status 193), 源文件永远压不了.
        """
        # clamp 到 0: suffix 本身超长时不能退化成负数切片 (那样会把整个 title 留下)
        budget = max(BaseMedia.NAME_MAX - len(tail.encode()), 0)
        if len(title.encode()) <= budget:
            return title + tail
        # 只切到完整 UTF-8 字符边界, 否则名字末尾会留半个汉字
        return title.encode()[:budget].decode('utf-8', 'ignore') + tail

    @classmethod
    def create_file_path(cls, path: str, suffix: str = '', suffix_number: int = 1, ext: Optional[str] = None):
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

        with cls._LOCK:
            while True:
                file_path = os.path.join(dirname, cls.fit_filename(title, f'-{suffix}_{suffix_number}.{ext}'))
                # file_path = os.path.join(dirname, f"{title}.{ext}")
                if not os.path.exists(file_path):
                    break
                suffix_number += 1
        return file_path
