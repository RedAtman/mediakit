"""
Usage:
python cli.py compress -t video -w 1 -f /path/to/folder
python cli.py change_file_extension --old_ext avi --new_ext mp4 -f /path/to/folder
python cli.py change_file_extension --old_ext mp4 --new_ext avi
"""

import argparse
import logging

from config import CONFIG


logger = logging.getLogger()


mapper_action = {
    "all": None,
    "compress": None,
    "trim": None,
    "change_file_extension": None,
}


def create_parser():
    parser = argparse.ArgumentParser(
        description="""
        Media Handler CLI;

        e.g.: \r\n
            %(prog)s compress -t video -w 2;
        """
    )
    parser.add_argument(
        "action",
        type=str,
        choices=mapper_action.keys(),
        default="all",
        help="Action to run",
    )
    parser.add_argument(
        "-f",
        "--folder",
        type=str,
        default=CONFIG.MEDIA_FILE_FOLDER,
        help="Folder to run",
    )
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        default="all",
        choices=("all", "video", "audio", "image"),
    )
    parser.add_argument("-w", "--worker", type=int, default=1, help="Number of workers")
    parser.add_argument(
        "-d", "--daemon", type=bool, default=True, choices=(True, False)
    )
    # parser.add_argument('-d', '--daemon', nargs="?", const=True)
    # parser.add_argument('--flag', action='store_true', help='Set the flag value to True')
    parser.add_argument("--old_ext", type=str, help="Old extension")
    parser.add_argument("--new_ext", type=str, help="New extension")
    return parser


def main():
    from src.schedulers import folder

    parser = create_parser()
    args = parser.parse_args()
    # logger.debug(args)
    # logger.debug(args.action)
    # logger.debug(type(args.__dict__))
    logger.debug(args.__dict__)
    scheduler = getattr(folder, args.action)
    # logger.debug(scheduler)
    result = getattr(scheduler, "core")(**args.__dict__)
    logger.info(result)


if __name__ == "__main__":
    main()
