import logging
import os
import shutil
import subprocess
import sys
import threading
from typing import IO, List, Optional, Sequence, Type, Union

from .process.parser import BaseStdoutParser
from .progress import BaseProgress


logger = logging.getLogger()

MIN_DISK_GB = 1


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

    # Optional coordinator for dynamic CPU throttling.
    # Set by src/schedulers/folder.py on startup.
    coordinator = None

    @classmethod
    def run(cls, command: Union[List[str], str], monitor: Optional[ProgressMonitor] = None, mode="standard", timeout: Optional[float] = None):
        """Run shell command.

        Args:
            command (Union[List[str], str]): _description_
            monitor (Optional[ProgressMonitor], optional): _description_. Defaults to None.
            mode (str, optional): _description_. Defaults to "standard". Options: ["standard", "pipe"]
            timeout (Optional[float], optional): Max seconds to wait. Defaults to None (no timeout).

        Returns:
            _type_: _description_
        """
        if mode == "pipe":
            return cls.pipe_execute(command)
        return cls.execute(command, monitor, timeout=timeout)

    @staticmethod
    def _check_disk_space(path: str = '.') -> None:
        try:
            usage = shutil.disk_usage(path)
            if usage.free < MIN_DISK_GB * (1024 ** 3):
                raise RuntimeError(
                    f"Insufficient disk space: {usage.free / (1024 ** 3):.1f}GB free "
                    f"(minimum: {MIN_DISK_GB}GB)"
                )
        except OSError:
            pass  # disk_usage may fail on some filesystems — proceed anyway

    @staticmethod
    def execute(command: Union[List[str], str], monitor: Optional[ProgressMonitor] = None, timeout: Optional[float] = None):
        """Execute shell command.

        Args:
            command (Union[List[str], str]): [description]
            TODO: Constraint command type to List[str] or str
            progress_bar (Optional[ProgressBar], optional): [description]. Defaults to None.
            timeout (Optional[float], optional): Max seconds to wait for process. Defaults to None (no timeout).

        Raises:
            TypeError: [description]
            subprocess.CalledProcessError: [description]
            TimeoutError: [description]

        Returns:
            [type]: [description]
        """
        if not isinstance(command, (list, str)):
            raise TypeError(f"command must be list or str. but got {type(command)}")

        if isinstance(command, list):
            command = list(filter(lambda x: x != ' ', command))

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
        coord = getattr(CommandExecutor, 'coordinator', None)

        CommandExecutor._check_disk_space()

        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=isinstance(command, str),
            encoding="utf-8",
        ) as process:
            if coord:
                coord.attach(process.pid)
            try:
                if monitor and process.stdout:
                    monitor.run(process.stdout)
                _stdout, _stderr = process.communicate(timeout=timeout)
                stdout = _stdout.strip()

                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, command,
                        output=stdout, stderr=_stderr,
                    )
                return stdout
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise TimeoutError(
                    f"Process '{' '.join(command) if isinstance(command, list) else command}' "
                    f"exceeded timeout of {timeout}s"
                ) from None
            finally:
                if coord:
                    coord.detach(process.pid)

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
