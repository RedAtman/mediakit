import os
import subprocess
import sys
import threading
from functools import partial

from logger import logger  # pylint: disable=W0611

from .tools import ProgressBar

__all__ = [
    'CommandExecutor',
]


class CommandExecutor:
    progress_bar = None

    def __init__(self, total: int = 0, title: str = ''):
        if total > 0 and title:
            self.progress_bar = partial(ProgressBar, total, title, fmt=ProgressBar.FULL)
        # logger.info((total, title, self.progress_bar))

    def run(self, command: list, progress_bar=True):
        if progress_bar and self.progress_bar:
            return self.execute(command, progress_bar=self.progress_bar())
        return self.execute(command)

    @staticmethod
    def execute(command: list, progress_bar=None):
        # logger.debug(progress_bar)
        if not isinstance(command, (list, str)):
            raise TypeError(f'command must be list or str. but got {type(command)}')

        logger.info(
            'Process: %s, Thread: %s, <Caller (%s) start...>, file: %s:%s %s',
            os.getpid(),
            threading.current_thread().name,
            # inspect.currentframe().f_code.co_name,
            sys._getframe().f_back.f_code.co_name,  # pylint: disable=E1101, protected-access
            sys._getframe().f_back.f_code.co_filename,  # pylint: disable=E1101, protected-access
            sys._getframe().f_back.f_code.co_firstlineno,   # pylint: disable=E1101, protected-access
            ' '.join(command) if isinstance(command, list) else command
        )
        with subprocess.Popen(
            command,
            # stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=isinstance(command, str),
            # bufsize=1,
            # universal_newlines=True,
            encoding='utf-8',
            # text=True,
        ) as process:
            if progress_bar:
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
                    'command: %s, returncode: %s, stdout: %s, _stderr: %s',
                    command, process.returncode, stdout, _stderr,
                )
                raise subprocess.CalledProcessError(process.returncode, command, _stderr)

            logger.debug(stdout)
            return stdout
