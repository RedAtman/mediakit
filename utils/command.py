import logging
import os
import subprocess
import sys
import threading
from typing import IO, List, Optional, Sequence, Type, Union

from .process.parser import BaseStdoutParser
from .progress import BaseProgress


logger = logging.getLogger()


__all__ = [
    "CommandExecutor",
]


class ProgressMonitor:

    def __init__(
        self,
        parser_class: Type[BaseStdoutParser],
        progress_list: Sequence[BaseProgress],
    ) -> None:
        if not issubclass(parser_class, BaseStdoutParser):
            raise TypeError(f"parser_class must be BaseStdoutParser. but got {type(parser_class)}")
        self.parser_class = parser_class
        if not isinstance(progress_list, list):
            raise TypeError(f"progress_list must be list. but got {type(progress_list)}")
        if not all(isinstance(progress, BaseProgress) for progress in progress_list):
            raise TypeError(f"All progress in progress_list must be BaseProgress. but got {progress_list}")
        self.progress_list = progress_list

    def run(self, stdout: IO[str]):
        parser = self.parser_class(stdout)
        for current in parser.parse():
            for progress in self.progress_list:
                progress.current = current


class CommandExecutor:

    @classmethod
    def run(cls, command: Union[List[str], str], monitor: Optional[ProgressMonitor] = None):
        if "|" in command:
            return cls.pipe_execute(command)
        return cls.execute(command, monitor)

    @staticmethod
    def execute(command: Union[List[str], str], monitor: Optional[ProgressMonitor] = None):
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
            # start_new_session=True,
        ) as process:
            if monitor and process.stdout:
                monitor.run(process.stdout)
            # if progress_bar and process.stdout:
            #     while process.stdout.readable():
            #         line = process.stdout.readline()
            #         if not line:
            #             progress_bar.done()
            #             break
            #         # logger.debug(line)
            #         # sys.stdout.write(line)
            #         # sys.stdout.flush()
            #         progress_bar.parse_current(line)

            _stdout, _stderr = process.communicate()
            stdout = _stdout.strip()

            if process.returncode != 0:
                # logger.exception(
                #     "process: %s, returncode: %s, command: %s, stdout: %s, stderr: %s",
                #     process.__dict__,
                #     process.returncode,
                #     command,
                #     stdout,
                #     _stderr,
                # )
                raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=_stderr)

            # logger.debug(stdout)
            return stdout

    @staticmethod
    def pipe_execute(command: Union[List[str], str]):
        """Execute shell command containing `|`."""
        assert "|" in command, f"command must contain '|'. but got {command}"
        if isinstance(command, str):
            command = command.split(" ")
        index = command.index("|")
        command1, command2 = command[:index], command[index + 1 :]
        process1 = subprocess.Popen(command1, stdout=subprocess.PIPE)
        process = subprocess.run(command2, stdin=process1.stdout, stdout=subprocess.PIPE)
        return process.stdout.decode("utf-8").strip()
