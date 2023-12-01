import time

from base.folder import BaseFolder
from base.video import Video
from logger import logger
from utils import TaskManager, decorator, exceptions
from utils.command import CommandExecutor


class Folder(BaseFolder):
    MEDIA_CLS = Video

    @decorator.timer
    def compress(self, callback_list=None):
        self._compress(path=self.path, callback_list=callback_list)

    @classmethod
    def _compress(cls, path='', callback_list=None):
        '''Multi-process batch file compression.

        Keyword Arguments:
            path {str} -- [Wait for the folder path to be compressed] (default: {''})
                e.g.: /usr/media/
            callback_list {list} -- [A list of callback function name after the file is compressed] (default: {None})
                e.g.: ['func', ...]
        '''
        callback_list = callback_list or []
        task_manager = TaskManager(max_workers=1)
        with task_manager.executor:
            for media in cls.get_medias(path):
                try:
                    task_manager.submit(getattr(media, 'quick_compress'), callback_list=callback_list)
                except exceptions.NotMediaException as err:
                    logger.error(err)
                    continue
                except Exception as err:
                    logger.exception(err)
            logger.info('Waiting for all subprocesses done...')

    @decorator.timer
    def trim(self, files, callback_list=None):
        self._trim(files, callback_list)

    @classmethod
    def _trim(cls, files=None, callback_list=None):
        '''Multi-process batch file trim.

        Arguments:
            files {[list]} -- [A list of dictionaries containing the path and trim_times of the file to be trimmed]
                e.g.: [
                    {
                        'path': '/usr/media/1.mp4',
                        'trim_times': (
                            ("00:50:22", "01:03:27"),
                            ("01:19:39", "01:37:04"), ...
                        )
                    },
                ]
            callback_list {[list]} -- [A list of callback function names after the file is trimmed] (default: {None})
        '''
        files = files or []
        callback_list = callback_list or []
        task_manager = TaskManager()
        with task_manager.executor:
            for file in files:
                suffix_number = 0
                for _time in file.get('trim_times'):
                    suffix_number += 1
                    try:
                        media = cls(file.get('path'))
                        task_manager.submit(
                            getattr(media, 'trim'),
                            time=_time,
                            suffix_number=suffix_number,
                        )
                    except exceptions.NotMediaException as err:
                        logger.error(err)
                        continue
                    except Exception as err:
                        logger.exception(err)
            logger.info('Waiting for all subprocesses done...')

    @decorator.timer
    def convert_images_to_video(self, image_format, bit_rate='5000k'):
        '''Convert images to video.

        Arguments:
            image_format {[str]} -- [Image format] (default: {'jpg'})
                e.g.: 'jpg', 'png', ...
            bit_rate {[str]} -- [Video bitrate] (default: {'5000k'})
                e.g.: '5000k', '10000k', ...

        TODO: delete image_format
        '''
        self._convert_images_to_video(self.path, image_format, bit_rate)

    @classmethod
    def _convert_images_to_video(cls, images_path, image_format, bit_rate='5000k'):
        create_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        new_file_path = f'{images_path}/output_{bit_rate}_1920_{create_time}.mp4'
        command = cls.MEDIA_CLS.ffmpeg_prefix + [
            # 关闭每帧都提醒是否overwrite
            '-pattern_type', 'glob',

            # 设置帧率
            '-r', '24',

            # 设置images文件路径,
            '-i', images_path + '/*.' + image_format,

            # 码率
            # '-b:v', bit_rate,

            # 线程(待验证)
            # '-threads', '4',

            # 画面缩放比率
            '-vf', 'scale=1920:-1',

            # 对video类型文件设置编码类型
            # '-c:v', 'libx264',
            # '-c:v', 'libx265',

            # 时长取最短的media
            # '-shortest',
            new_file_path,
        ]
        CommandExecutor.execute(command)
        return cls.MEDIA_CLS(path=new_file_path)
