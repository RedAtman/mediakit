#!/usr/bin/env python3
"""
Usage:
    mediakit compress -t video -w 1 -f /path/to/folder
    mediakit change_file_extension --old_ext avi --ext mp4 -f /path/to/folder
    mediakit change_file_extension --old_ext mp4 --ext avi
    mediakit convert_format -t video -f /path/to/folder

Also available via direct python invocation:
    python cli.py compress -t video -w 1 -f /path/to/folder
"""

import logging

from utils.cli import create_parser


logger = logging.getLogger()


def main():
    parser = create_parser()
    args = parser.parse_args()

    from src.schedulers import folder

    scheduler = getattr(folder, args.action)
    # logger.debug(scheduler)
    result = getattr(scheduler, "core")(**args.__dict__)
    logger.info(result)


if __name__ == "__main__":
    main()
