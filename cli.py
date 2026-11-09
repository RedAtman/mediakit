#!/usr/bin/env python3
"""
Usage:
    mediakit compress -t video -w 1 -f /path/to/folder
    mediakit change_file_extension --old_ext avi --ext mp4 -f /path/to/folder
    mediakit change_file_extension --old_ext mp4 --ext avi
    mediakit convert_format -t video -f /path/to/folder
    mediakit dedupe [--apply]

Also available via direct python invocation:
    python cli.py compress -t video -w 1 -f /path/to/folder
"""

import logging

from utils.cli import create_parser

logger = logging.getLogger()


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.watch:
        from src.schedulers.watcher import WatcherScheduler

        scheduler = WatcherScheduler()
    else:
        from src.schedulers.folder import SCHEDULERS

        try:
            scheduler = SCHEDULERS[args.action]
        except KeyError:
            # utils.cli 的词表与实现由 src/schedulers/folder.py 在 import 期校验, 走到这里
            # 说明 argv 绕过了 argparse 的 choices
            raise SystemExit(f'unknown action: {args.action}')
    result = getattr(scheduler, 'core')(**args.__dict__)
    logger.info(result)


if __name__ == '__main__':
    main()
