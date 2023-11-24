import functools
import json
import os
import re
import subprocess

from logger import logger
from utils import exceptions, execute, is_media

__all__ = [
    'BaseMedia',
]


class BaseMedia:
    '''docstring for BaseMedia'''
    def __init__(self, path):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found at path: {path}')
        if not is_media(path):
            raise exceptions.NotMediaException(101, f'File is not media file: {path}')
        self.path = path
        self.dirname, self.title, self.ext = self.get_file_info(path)

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
        try:
            result = execute(command)
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
        return re.findall("""(.*)\\/([^<>/\\\\|:''\\?]+)\\.(\\w+)$""", path)[0]
