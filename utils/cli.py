import argparse
import logging

from config import CONFIG

logger = logging.getLogger()


mapper_action = {
    'all': None,
    'compress': None,
    'trim': None,
    'scale': None,
    'change_file_extension': None,
    'convert_format': None,
    'save_text': None,
    'combine': None,
    'reverse': None,
    'decode': None,
    'delete_voice': None,
    'save_metadata': None,
    'set_metadata': None,
    'images_to_video': None,
    'concat': None,
    'stop': None,
    'dedupe': None,
}


def create_parser():
    parser = argparse.ArgumentParser(
        description="""
        MediaKit CLI;

        e.g.: \r\n
            %(prog)s compress -t video -w 2;
        """
    )
    parser.add_argument('action', type=str, choices=mapper_action.keys(), default='compress', help='Action to run')
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
        help='CPU limit per worker (100 = one core). When not set, uses auto mode with dynamic throttling. At runtime, send SIGUSR1 to cycle through fixed profiles: unlimited -> 100%% -> 50%% -> 25%% (SIGUSR1 cannot carry a value, so it uses a fixed cycle)',
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
