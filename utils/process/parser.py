import abc
import logging
import re
from typing import IO


logger = logging.getLogger()


class BaseStdoutParser:

    def __init__(self, stdout: IO[str]):
        self.stdout: IO[str] = stdout

    def parse(self):
        while self.stdout.readable():
            line = self.stdout.readline()
            if not line:
                break
            # logger.debug(line)
            # sys.stdout.write(line)
            # sys.stdout.flush()
            current = self.parse_stdout_line(line)
            if current:
                yield int(current)

    @abc.abstractmethod
    def parse_stdout_line(self, stdout_line: str) -> int:
        raise NotImplementedError


class FfmpegCurrentFrameStdoutParser(BaseStdoutParser):

    def parse_stdout_line(self, stdout_line: str):
        current = re.findall(r"frame=\s*(\d+)", stdout_line)
        if current:
            return current[-1]
