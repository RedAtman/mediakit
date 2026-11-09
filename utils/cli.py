import argparse
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
import logging

from config import CONFIG
from utils.video import VideoResolution

logger = logging.getLogger()


def _version() -> str:
    """版本号唯一来源: 打包元数据 ([project].version in pyproject.toml)

    ponytail: 不在这里重复一份版本号字符串. 未安装的源码树查不到 dist 元数据,
    此时报 unknown 而不是去猜一个可能过期的值
    """
    try:
        return distribution_version(CONFIG.PROJECT_NAME)
    except PackageNotFoundError:
        return 'unknown'


def _resolution_arg(value: str) -> VideoResolution:
    """argparse type: 在命令行解析阶段就校验分辨率, 避免批量任务逐个文件失败

    ponytail: 不自建 choices 列表, 可选值以 VideoResolution 枚举为唯一来源
    """
    try:
        return VideoResolution.parse(value)
    except ValueError as err:
        raise argparse.ArgumentTypeError(str(err)) from err


def _fps_arg(value: str) -> int:
    """argparse type: ffmpeg -r 不接受 <=0"""
    fps = int(value)
    if fps < 1:
        raise argparse.ArgumentTypeError(f'fps must be >= 1, got {fps}')
    return fps


# CLI 认得的所有 action; src/schedulers/folder.py::SCHEDULERS 必须全部实现,
# 在 import 时校验 (见该模块), 这样加 action 漏改一边会立刻炸而不是跑到一半 AttributeError.
# 'trim' 没有 scheduler: Folder.trim 需要 trim_times 而 CLI 没有对应参数, 历史上
# `mediakit trim` 直接 AttributeError. 实现之前不放进 choices, 至少报错是清楚的
ACTIONS: tuple[str, ...] = (
    'compress',
    'scale',
    'change_file_extension',
    'convert_format',
    'save_text',
    'combine',
    'reverse',
    'decode',
    'delete_voice',
    'save_metadata',
    'set_metadata',
    'images_to_video',
    'concat',
    'stop',
    'dedupe',
)


def create_parser(actions: tuple[str, ...] = ACTIONS):
    parser = argparse.ArgumentParser(
        description="""
        MediaKit CLI;

        e.g.: \r\n
            %(prog)s compress -t video -w 2;
        """
    )
    parser.add_argument('action', type=str, choices=actions, default='compress', help='Action to run')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {_version()}')
    parser.add_argument(
        '-f',
        '--folder',
        type=str,
        default=CONFIG.MEDIA_FILE_FOLDER,
        # default=os.getcwd(),
        help='Folder to run',
    )
    parser.add_argument('-t', '--type', type=str, default='all', choices=('all', 'video', 'audio', 'image'))
    parser.add_argument('-w', '--max_workers', type=int, default=CONFIG.MAX_WORKERS, help='Number of workers')
    parser.add_argument(
        '-c',
        '--cpu-limit',
        type=int,
        help=(
            'CPU limit per worker (100 = one core). When not set, uses auto mode with dynamic throttling. '
            'At runtime, send SIGUSR1 to cycle through fixed profiles: unlimited -> 100%% -> 50%% -> 25%% '
            '(SIGUSR1 cannot carry a value, so it uses a fixed cycle)'
        ),
    )
    parser.add_argument('-d', '--daemon', type=bool, default=True, choices=(True, False))
    # parser.add_argument('-d', '--daemon', nargs="?", const=True)
    # parser.add_argument('--flag', action='store_true', help='Set the flag value to True')
    parser.add_argument(
        '--recursive', action='store_true', default=False, help='Watch subdirectories (default: non-recursive)'
    )
    parser.add_argument(
        '--no-scan-existing', action='store_true', default=False, help='Skip processing existing files at startup'
    )
    parser.add_argument(
        '--folder-file',
        type=str,
        default=None,
        help='Path to a text file with folder paths (one per line, # comments skipped)',
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        default=False,
        help='Watch folder for new files and process them (combine with -f, -t, -a)',
    )
    parser.add_argument('--old_ext', type=str, default=argparse.SUPPRESS, help='Old extension')
    parser.add_argument('--ext', type=str, default=argparse.SUPPRESS, help='New extension')
    parser.add_argument(
        '--resolution',
        type=_resolution_arg,
        default=None,
        help='Compress: target resolution, e.g. FHD / 1920x1080 / UHD (enum name or WxH, case-insensitive). '
        'Downscale only, keeps aspect ratio. Default: COMPRESS_RESOLUTION env (HD)',
    )
    parser.add_argument(
        '--fps', type=_fps_arg, default=None, help='Compress: output fps (>=1). Default: COMPRESS_FPS env (24)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        default=False,
        help='Force stop: immediately kill all mediakit and ffmpeg processes',
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        default=False,
        help='Dedupe: actually move duplicate files to Trash (default is dry-run)',
    )
    parser.add_argument(
        '--db', type=str, default='db.db', help='Dedupe: path to the media database (for survivor preference)'
    )
    parser.add_argument('--concat-list', type=str, default='', help='Concat: path to a concat demuxer list file')
    parser.add_argument('--images-path', type=str, default='', help='Images: folder containing the image sequence')
    parser.add_argument('--image-format', type=str, default='jpg', help='Images: image format (jpg/png/...)')
    parser.add_argument('--bit-rate', type=str, default='5000k', help='Images: output video bitrate')
    return parser
