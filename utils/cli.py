import argparse
import logging

from config import CONFIG


logger = logging.getLogger()


mapper_action = {
    "all": None,
    "compress": None,
    "trim": None,
    "scale": None,
    "change_file_extension": None,
    "convert_format": None,
    "save_text": None,
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
        # default=os.getcwd(),
        help="Folder to run",
    )
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        default="all",
        choices=("all", "video", "audio", "image"),
    )
    parser.add_argument(
        "-w",
        "--max_workers",
        type=int,
        default=CONFIG.MAX_WORKERS,
        help="Number of workers",
    )
    parser.add_argument(
        "-c",
        "--cpu-limit",
        type=int,
        help="CPU limit per worker (100 = one core). When not set, uses auto mode with dynamic throttling. At runtime, send SIGUSR1 to cycle through fixed profiles: unlimited -> 100%% -> 50%% -> 25%% (SIGUSR1 cannot carry a value, so it uses a fixed cycle)",
    )
    parser.add_argument("-d", "--daemon", type=bool, default=True, choices=(True, False))
    # parser.add_argument('-d', '--daemon', nargs="?", const=True)
    # parser.add_argument('--flag', action='store_true', help='Set the flag value to True')
    parser.add_argument("--old_ext", type=str, default=argparse.SUPPRESS, help="Old extension")
    parser.add_argument("--ext", type=str, default=argparse.SUPPRESS, help="New extension")
    return parser
