from base.media import BaseMedia
from config import CONFIG
from logger import logger
from mixins import whispers


class Audio(
    BaseMedia,
    # whispers.MixinMediaWhisper,
    whispers.MixinMediaFasterWhisper,
    # whispers.MixinMediaWhisperCPP,
):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def trim(self, trim_time=()):
        return self._trim(self.path, trim_time=trim_time)

    @classmethod
    def _trim(cls, path, trim_time):
        '''Trim media file.

        Arguments:
            path {[str]} -- [Media file path]
            trim_time {[tuple]} -- [Trim time tuple, (start_time, end_time)]

        Returns:
            [str] -- [Trimmed media file path]
        '''

        if not trim_time:
            raise ValueError('trim_time is empty')
        if len(trim_time) != 2:
            raise ValueError('trim_time length is not 2')
        start_time, end_time = trim_time
        new_file_path = cls.create_file_path(path)
        command = f'ffmpeg -y -i "{path}" -c copy -ss {start_time} -to {end_time} "{new_file_path}"'
        cls._executor.execute(command)
        return command
