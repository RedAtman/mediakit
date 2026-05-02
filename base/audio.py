from typing import Sequence

from src.mixins.transcriber import MixinMediaTranscriber
from utils import decorator
from utils.command import CommandExecutor

from .media import BaseMedia


__all__ = [
    "Audio",
]


class Audio(
    BaseMedia,
    MixinMediaTranscriber,
):
    _INCLUDE_TYPE = [
        "audio",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def trim(self, trim_time=()):
        return self._trim(self.path, trim_time=trim_time)

    @decorator.timer
    @classmethod
    def _trim(cls, path: str, trim_time: Sequence[str] = ()):
        """Trim media file.

        Arguments:
            path {[str]} -- [Media file path]
            trim_time {[tuple]} -- [Trim time tuple, (start_time, end_time)]

        Returns:
            [str] -- [Trimmed media file path]
        """

        if not trim_time:
            raise ValueError("trim_time is empty")
        if len(trim_time) != 2:
            raise ValueError("trim_time length is not 2")
        start_time, end_time = trim_time
        new_file_path = cls.create_file_path(path)
        command = f'ffmpeg -y -i "{path}" -c copy -ss {start_time} -to {end_time} "{new_file_path}"'
        CommandExecutor.run(command)
        return cls, command, new_file_path
