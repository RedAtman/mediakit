import functools
import json
import logging
import os
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Type

from base import BaseFolder, BaseMedia
from config import CONFIG
from src.mixins.db import SqlAlchemyFolderMixin
from utils import decorator, exceptions, executor
from utils.command import CommandExecutor
from utils.tools import Dict2Obj


logger = logging.getLogger()


class Folder(
    BaseFolder,
    SqlAlchemyFolderMixin,
):
    def __init__(self, path: str, media_type: str = "video"):
        super().__init__(path)
        self.MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(
            media_type, BaseMedia
        )

    @functools.cached_property
    def medias(self):
        return self.medias_(self.path, media_type=self.MEDIA_CLS.__name__.lower())

    @classmethod
    # @functools.cache
    def medias_(
        cls, path: str, media_type: str = "video"
    ) -> Generator[BaseMedia, Any, None]:
        MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(
            media_type, BaseMedia
        )
        for file in cls.get_files(path):
            try:
                media = MEDIA_CLS(file)
                yield media
            except exceptions.NotMediaException:
                continue
            except Exception as err:
                logger.exception(err)
                continue
        # try:
        #     while True:
        #         file = next(cls.get_files(path))
        #         try:
        #             media = MEDIA_CLS(file)
        #             logger.warning(media, file)
        #             yield media
        #         except exceptions.NotMediaException:
        #             continue
        #         except Exception as err:
        #             logger.exception(err)
        #             continue
        # except StopIteration:
        #     pass

    def run(self, media_method: str):
        return self.run_(
            media_method,
            path=self.path,
            media_type=self.MEDIA_CLS.__name__.lower(),
        )

    @classmethod
    def run_(
        cls,
        media_method: str,
        *args: Any,
        path: str = CONFIG.MEDIA_FILE_FOLDER,
        media_type: str = "video",
        max_workers: int = CONFIG.MAX_WORKERS,
        callback_list: List[Callable[..., Any]] = [],
        **kwargs: Dict[str, Any],
    ):
        """Run the specified method of all media in the folder.

        Arguments:
            media_method {str} -- [media method name]
            path {str} -- [folder path] (default: {CONFIG.MEDIA_FILE_FOLDER})
            media_type {str} -- [media type] (default: {'video'})
            max_workers {int} -- [max_workers] (default: {CONFIG.MAX_WORKERS})
            callback_list {List[Callable[..., Any]]} -- [callback function list] (default: {[]})

        Returns:
            [list] -- [The return value of each media method]
            e.g.: [
                {
                    code: <ResultStatus.SUCCESS: 200>,
                    msg: 'Success',
                    data: {},
                },
            ]

        Usage:
        e.g.:
            Folder.run_(
                'compress',
                *args,
                callback_list=[callback, ],
                **kwargs,
            )
        """
        MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(
            media_type, BaseMedia
        )
        _media_method = getattr(MEDIA_CLS, media_method, None)
        if _media_method is None:
            logger.warning("Unimplemented method: %s", media_method)
            raise NotImplementedError
        if not isinstance(_media_method, Callable):
            logger.warning(f"{MEDIA_CLS} has not implemented {_media_method} method.")
            raise TypeError
        medias = cls.medias_(path, media_type)
        logger.debug(
            ("run_", MEDIA_CLS, medias, type(medias), path, media_type, callback_list)
        )
        return cls.run__(
            media_method,
            *args,
            medias=medias,
            max_workers=max_workers,
            callback_list=callback_list,
            **kwargs,
        )

    @classmethod
    def run__(
        cls,
        media_method: str,
        *args: Any,
        medias: Optional[Generator[BaseMedia, None, None]] = None,
        max_workers: int = CONFIG.MAX_WORKERS,
        callback_list: List[Callable[..., Any]] = [],
        **kwargs: Any,
    ):
        if medias is None:
            raise TypeError("medias is None.")
        tasks = [getattr(media, media_method) for media in medias]
        return cls.run___(
            *args,
            tasks=tasks,
            max_workers=max_workers,
            callback_list=callback_list,
            **kwargs,
        )

    @staticmethod
    def run___(
        *args: Any,
        tasks: List[Callable] = [],
        max_workers: int = CONFIG.MAX_WORKERS,
        callback_list: List[Callable[..., Any]] = [],
        **kwargs: Any,
    ):
        task_manager = executor.TaskManager(max_workers)
        _ = list(
            task_manager.submit_all(tasks, *args, callback_list=callback_list, **kwargs)
        )
        return [future.result() for future in task_manager.futures]

    @property
    def meta(self):
        return Dict2Obj(self.read_meta(self.path))

    @staticmethod
    def read_meta(path: str) -> Dict[str, str]:
        """Read media meta from meta.json under the folder.

        Arguments:
            path {str} -- [folder path]

        Returns:
            [dict] -- [media meta]
            e.g.: {
                "video": {
                    "path": "20210831_ProRes-444_BT2020L_OriRes_25_UHQ_mb05.mov",
                    "title": "20210831_中国北京天坛祈年殿",
                    "artist": "aQuantum,一枚量子",
                    "category": "time_lapse",
                    "camera": "sony_a7r2",
                    "lens": "laowa_12mm_f2.8",
                    "keywords": "天坛,祈年殿,北京,中国,中国北京,中国"
                },
                "resolution": "4k",
                "reverse": False,
                "crop": {
                    "w": 4096,
                    "h": 2160,
                    "x": 0,
                    "y": 100
                },
                "audio": {
                    "path": "/Users/nut/Downloads/Illuminate (Trailer Music) - Dirk Leupolz.mp3",
                    "defer": 15.3,
                    "fade_duration": 1
                },
                "watermark": {
                    "path": "/Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png",
                    "transparent": 0.3
                }
            }
        """
        if not os.listdir(path).count("meta.json"):
            raise FileNotFoundError(f"File not found: {path}/meta.json")
        try:
            with open(os.path.join(path, "meta.json"), "r", encoding="utf-8") as fd:
                content = fd.read()
                return json.loads(content).get("video", {})
        except Exception as err:
            logger.exception(err)
            raise err

    @decorator.timer
    def trim(
        self,
        files: List[Dict[str, Any]],
        callback_list: List[Callable[..., Any]] = [],
        max_workers: int = CONFIG.MAX_WORKERS,
    ):
        self._trim(files, callback_list, max_workers)

    @classmethod
    def _trim(
        cls,
        files: List[Dict[str, Any]] = [],
        callback_list: List[Callable[..., Any]] = [],
        max_workers: int = CONFIG.MAX_WORKERS,
    ):
        """Multi-process batch file trim.

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
        """
        callback_list = callback_list or []
        task_manager = executor.TaskManager(max_workers)
        # TODO: use task_manager.submit_all
        with task_manager.executor:
            for file in files:
                suffix_number = 0
                for _time in file.get("trim_times"):
                    suffix_number += 1
                    try:
                        media = cls(file.get("path"))
                        task_manager.submit(
                            getattr(media, "trim"),
                            time=_time,
                            suffix_number=suffix_number,
                        )
                    except exceptions.NotMediaException as err:
                        logger.error(err)
                        continue
                    except Exception as err:
                        logger.exception(err)
            logger.info("Waiting for all subprocesses done...")

    @decorator.timer
    def convert_images_to_video(self, image_format: str, bit_rate="5000k"):
        """Convert images to video.

        Arguments:
            image_format {[str]} -- [Image format] (default: {'jpg'})
                e.g.: 'jpg', 'png', ...
            bit_rate {[str]} -- [Video bitrate] (default: {'5000k'})
                e.g.: '5000k', '10000k', ...

        TODO: delete image_format
        """
        self._convert_images_to_video(self.path, image_format, bit_rate)

    @classmethod
    def _convert_images_to_video(
        cls, images_path: str, image_format: str, bit_rate="5000k", media_type="image"
    ):
        create_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        new_file_path = f"{images_path}/output_{bit_rate}_1920_{create_time}.mp4"
        MEDIA_CLS: Type[BaseMedia] = BaseMedia._SUBCLASS_MAPPER.get(
            media_type, BaseMedia
        )
        command = MEDIA_CLS._FFMPEG_PREFIX + [
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
            # '-threads', '4',
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
        return cls, command, new_file_path
