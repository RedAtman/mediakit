from functools import partial
import logging
import os
import subprocess
import sys
import threading
from typing import List, Optional, Union

from .tools import ProgressBar


logger = logging.getLogger()


__all__ = [
    "CommandExecutor",
]


class CommandExecutor:
    progress_bar = None

    def __init__(self, total: int = 0, title: str = ""):
        if total > 0 and title:
            self.progress_bar = partial(ProgressBar, total, title, fmt=ProgressBar.FULL)
        # logger.info((total, title, self.progress_bar))

    def run(self, command: List[str], progress_bar=True):
        if progress_bar and self.progress_bar:
            return self.execute(command, progress_bar=self.progress_bar())
        return self.execute(command)

    @staticmethod
    def execute(
        command: Union[List[str], str], progress_bar: Optional[ProgressBar] = None
    ):
        """Execute shell command.

        Args:
            command (Union[List[str], str]): [description]
            TODO: Constraint command type to List[str] or str
            progress_bar (Optional[ProgressBar], optional): [description]. Defaults to None.

        Raises:
            TypeError: [description]
            subprocess.CalledProcessError: [description]

        Returns:
            [type]: [description]
        """
        if not isinstance(command, (list, str)):
            raise TypeError(f"command must be list or str. but got {type(command)}")

        logger.info(
            "Process: %s, Thread: %s, Caller: %s:%s:%s, Command: %s",
            os.getpid(),
            threading.current_thread().name,
            # inspect.currentframe().f_code.co_name,
            sys._getframe().f_back.f_code.co_filename,
            sys._getframe().f_back.f_code.co_firstlineno,
            sys._getframe().f_back.f_code.co_name,
            " ".join(command) if isinstance(command, list) else command,
        )
        with subprocess.Popen(
            command,
            # stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=isinstance(command, str),
            # bufsize=1,
            # universal_newlines=True,
            encoding="utf-8",
            # text=True,
        ) as process:
            if progress_bar and process.stdout:
                while process.stdout.readable():
                    line = process.stdout.readline()
                    if not line:
                        progress_bar.done()
                        break
                    # logger.debug(line)
                    # sys.stdout.write(line)
                    # sys.stdout.flush()
                    progress_bar.parse_current(line)

            _stdout, _stderr = process.communicate()
            stdout = _stdout.strip()

            if process.returncode != 0:
                logger.exception(
                    "process: %s, returncode: %s, command: %s, stdout: %s, stderr: %s",
                    process.__dict__,
                    process.returncode,
                    command,
                    stdout,
                    _stderr,
                )
                raise subprocess.CalledProcessError(
                    process.returncode, command, output=stdout, stderr=_stderr
                )

            # logger.debug(stdout)
            return stdout
