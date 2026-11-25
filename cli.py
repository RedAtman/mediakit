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

from src.config_file import ConfigError
from utils.cli import create_parser

logger = logging.getLogger()


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.init_config:
        from src.config_file import write_starter_config

        try:
            target = write_starter_config(args.config)
        except FileExistsError as err:
            raise SystemExit(str(err)) from None
        print(f'wrote starter config: {target}')
        print('next: add [[watch.folders]] (or [watch] folders_file) to it, then run')
        print('      mediakit compress -t video --watch')
        return

    if args.action is None:
        raise SystemExit('an action is required (e.g. `mediakit compress ...`); see --help')

    if args.action != 'stop':
        # `stop` 例外: 配置写坏了也必须能停掉正在跑的守护进程.
        # engine() 是懒建的, 所以只要在调度器之前把路径应用上去就够.
        from src.config_file import apply_database_path, load_settings

        try:
            apply_database_path(load_settings(args.config))
        except ConfigError as err:
            # 与下面 core() 的处理器同一个契约: 配置错给一行提示, 不留 traceback
            raise SystemExit(f'config error: {err}') from None

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
    try:
        result = getattr(scheduler, 'core')(**args.__dict__)
    except ConfigError as err:
        # 配置错不是崩溃: 打一条人读得懂的错并退出, 排错时无需翻 traceback
        raise SystemExit(f'config error: {err}') from None
    logger.info(result)


if __name__ == '__main__':
    main()
