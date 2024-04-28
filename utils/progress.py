import abc
import re
import sys
from typing import IO, Any, Dict, Tuple


class CallHookMetaClass(type):
    """Hook __call__ method to call __after_init__ method after __init__ method.
    """
    def __call__(cls, *args, **kwargs):
        obj = type.__call__(cls, *args, **kwargs)
        obj.__after_init__()
        return obj


class BaseProgress(metaclass=CallHookMetaClass):
    """Base class for progress.

    Args:
        metaclass (_type_, optional): _description_. Defaults to CallHookMetaClass.
    """

    def __init__(self, total: int, *args: Tuple[Any, ...], **kwargs: Dict[str, Any]):
        if not isinstance(total, int):
            raise TypeError(f"total must be int. but got {type(total)}")
        if total <= 0:
            raise ValueError(f"total must be greater than 0. but got {total}")
        self.total: int = total
        self._current: int = 0

    # current = property(fget=lambda self: self._current)

    @property
    def current(self) -> int:
        return self._current

    @current.setter
    def current(self, value: int):
        self._current = value
        self.call()

    @property
    def percent(self) -> float:
        return self.current / self.total

    @abc.abstractmethod
    def call(self):
        raise NotImplementedError

    def __after_init__(self):
        return


class StdoutProgress(BaseProgress):
    """Print a progress bar to `sys.stdout`.

    Arguments:
        total {[int]} -- [Total count]
        title {[str]} -- [Title of the progress bar] (default: {'Progress'})
        width {[int]} -- [Width of the progress bar] (default: {40})
        fmt {[str]} -- [Format of the progress bar] (default: {DEFAULT})
        output {[sys.stderr]} -- [Output of the progress bar] (default: {sys.stderr})

    Usage:
        progress = StdoutProgress(10)
        for i in range(0, 11):
            progress.current = i
            time.sleep(0.1)
        >>>
        StdoutProgress: [##########          ] 50%
    """

    WIDTH: int = 50
    SYMBOL: str = "█"
    SYMBOL: str = "#"
    assert len(SYMBOL) == 1
    DEFAULT: str = "%(bar)s%(percent)3d%%: %(title)s"
    FULL: str = "%(bar)s %(current)d/%(total)d (%(percent)3d%%) %(remaining)d %(title)s"

    def __init__(
        self,
        total: int,
        title: str = "",
        width: int = WIDTH,
        fmt: str = DEFAULT,
        # output: IO[str] = sys.stderr,
        output: IO[str] = sys.stdout,
    ):
        super().__init__(total)
        self.title = title or self.__class__.__name__
        self.width = width
        self.output: IO[str] = output
        self.fmt = re.sub(
            r"(?P<name>%\(.+?\))d",
            rf"\g<name>{len(str(total))}d",
            fmt,
        )

    def __after_init__(self):
        self._call()

    def call(self):
        # Cursor up one line: to use ANSI escape sequences
        # sys.stdout.write("\033[F")
        print("\033[F", file=self.output, end="")

        # print the progress bar
        self._call()

    def _call(self):
        size = int(self.width * self.percent)

        args = {
            "total": self.total,
            "bar": "[" + self.SYMBOL * size + " " * (self.width - size) + "]",
            "current": self.current,
            "percent": self.percent * 100,
            "remaining": self.total - self.current,
            "title": self.title,
        }

        # print(self.fmt % args, file=self.output, end="\n")
        print(self.fmt % args, file=self.output)


from src.models import Media


class MediaStateProgress(BaseProgress):

    def __init__(self, total: int, model: Media):
        super().__init__(total)
        self.model = model

    def call(self):
        self.model.update_state("compress", self.percent)


if __name__ == "__main__":
    import time

    print(StdoutProgress)
    progress = StdoutProgress(10)
    for i in range(0, 11):
        progress.current = i
        time.sleep(0.1)
    print(progress)
    # media = Media.get(md5="9b364cebea51dcd4315ee96d11fc7aff")
    model = Media.get(md5="2d17da54164e43c9962decd2103a4798")
    print(model)
    print(MediaStateProgress)
    progress = MediaStateProgress(100, model)
    for i in range(0, 101):
        progress.current = i
        time.sleep(0.1)
    print(progress)
