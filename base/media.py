import functools
import json
import os
import subprocess

from logger import logger
from utils import exceptions, is_media
from utils.command import CommandExecutor

__all__ = [
    'BaseMedia',
]


class BaseMedia:
    '''docstring for BaseMedia'''
    def __init__(self, path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found at path: {path}')
        if not os.path.isfile(path):
            raise exceptions.NotMediaException(101, f'Path is not a file: {path}')
        if not is_media(path):
            raise exceptions.NotMediaException(101, f'File is not media file: {path}')
        self.path = path
        self.dirname, self.title, self.ext = self.get_file_info(path)
        self.executor = CommandExecutor(total=self.frames_count, title=self.path)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.path})'

    @functools.cached_property
    def frames_count(self):
        '''Get media file frames count.

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

            # Unverified.
            ffmpeg -i input.mp4 -vcodec copy -acodec copy -f null /dev/null 2>&1 | grep 'frame=' | cut -f 2 -d ' '
            ffprobe -i input.mp4 -print_format json -loglevel fatal -show_streams -count_frames -select_streams v
            ffprobe -v error -select_streams v:0 -show_entries stream=avg_frame_rate \
                -of default=noprint_wrappers=1:nokey=1 input.mp4
            ffmpeg -i input.mp4 -map 0:v:0 -c copy -f null -

        '''
        try:
            result = CommandExecutor.execute(
                f'ffprobe -v error -select_streams v -show_streams "{self.path}" | \
                    grep nb_frames | sed -e s/nb_frames=//'
            )
            return int(result)
        except ValueError as err:
            logger.exception(err)
            result = CommandExecutor.execute(
                f'ffprobe -v error -hwaccel auto -count_frames -select_streams v:0 -show_entries stream=nb_read_frames \
                    -of default=nokey=1:noprint_wrappers=1 "{self.path}"'
            )
            return int(result)
        except subprocess.CalledProcessError as err:
            logger.exception(err)
            raise err
        except Exception as err:
            logger.exception(err)
            raise err

    @functools.cached_property
    def metadata(self):
        return self.get_metadata(self.path)

    @classmethod
    def get_metadata(cls, path):
        '''Get media file metadata.

        Arguments:
            path {[str]} -- [Media file path]

        Returns:
            [type] -- [description]
        '''
        command = [
            'ffprobe', '-v', 'quiet', '-show_format',
            '-show_streams', '-print_format', 'json', path.strip()
        ]
        command = f'ffprobe -v quiet -show_format -show_streams -print_format json {path.strip()}'
        try:
            result = CommandExecutor.execute(command)
        except subprocess.CalledProcessError as err:
            logger.exception(err)
            raise err
        try:
            metadata = json.loads(result)
        except Exception as err:
            raise TypeError(f'{type(result)} is not JSONable') from err
        return metadata

    @functools.cached_property
    def width_height(self):
        '''Get media file width and height. Unit:pixel
        '''
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
        '''Get media file bitrate. Unit:kb/s'''
        bitrate = self.metadata.get('streams')[0].get(
            'bit_rate') or self.metadata.get('format').get('bit_rate')
        return float(bitrate)

    @functools.cached_property
    def duration(self):
        '''Get media file duration. Unit:second'''
        # result = subprocess.run([
        #     "ffprobe", "-v", "error", "-show_entries",
        #     "format=duration", "-of",
        #     "default=noprint_wrappers=1:nokey=1", self.path],
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.STDOUT)
        # return float(result.stdout)

        return self.metadata.get('streams')[0].get('duration')

    @staticmethod
    def get_file_info(path):
        '''Get file info.: dirname, title, ext.

        Arguments:
            path {[str]} -- [File path]

        Returns:
            [tuple] -- [dirname, title, ext]
        '''
        title, ext = os.path.splitext(os.path.basename(path))
        return os.path.dirname(path), title, ext[1:]
