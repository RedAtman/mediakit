import functools
import re
import sys
from typing import IO, Any, Callable, Union

from tqdm import tqdm

from src.models import Media


def wrapper_setter(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(self: 'BaseProgress', value):
        value = getattr(self, f'__before_{func.__name__}_setter__')(value)
        result = func(self, value)
        result = getattr(self, f'__after_{func.__name__}_setter__')(value)
        return result

    return wrapper


class BaseProgress:
    """Base class for progress.

    Args:
        metaclass (_type_, optional): _description_. Defaults to CallHookMetaClass.
    """

    PERCENT_STEP = 0.001

    def __init__(self, total: int, *args: tuple[Any, ...], **kwargs: dict[str, Any]):
        if not isinstance(total, int):
            raise TypeError(f'total must be int. but got {type(total)}')
        if total <= 0:
            raise ValueError(f'total must be greater than 0. but got {total}')
        self.total: int = total
        self._current: int = 0
        self._percent: float = 0.0
        # for percent step
        self._previous_step_percent: float = self._percent - self.PERCENT_STEP

    # current = property(fget=lambda self: self._current)

    @property
    def current(self) -> int:
        return self._current

    @current.setter
    @wrapper_setter
    def current(self, value: int):
        if not isinstance(value, int):
            raise TypeError(f'current must be int. but got {type(value)}')
        self._current = value
        self.percent = self.current / self.total

    @property
    def percent(self) -> float:
        return self._percent

    @percent.setter
    @wrapper_setter
    def percent(self, value: float):
        self._percent = value
        if abs(value - self._previous_step_percent) >= self.PERCENT_STEP:
            self.__after_percent_step__()
            self._previous_step_percent = value

    def __before_current_setter__(self, value: int):
        return value

    def __after_current_setter__(self, value: int):
        return value

    def __before_percent_setter__(self, value: Union[int, float]):
        return value

    def __after_percent_setter__(self, value: Union[int, float]):
        return value

    def __after_percent_step__(self):
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
    SYMBOL: str = '█'
    SYMBOL: str = '#'
    assert len(SYMBOL) == 1
    DEFAULT: str = '%(bar)s%(percent)3d%%: %(title)s'
    FULL: str = '%(bar)s %(current)d/%(total)d (%(percent)3d%%) %(remaining)d %(title)s'

    def __init__(
        self,
        total: int,
        title: str = '',
        width: int = WIDTH,
        fmt: str = DEFAULT,
        # output: IO[str] = sys.stderr,
        output: IO[str] = sys.stdout,
    ):
        super().__init__(total)
        self.title = title or self.__class__.__name__
        self.width = width
        self.output: IO[str] = output
        self.fmt = re.sub(r'(?P<name>%\(.+?\))d', rf'\g<name>{len(str(total))}d', fmt)

    def cursor_up(self, num: int = 1):
        # Cursor up one line: to use ANSI escape sequences
        # sys.stdout.write("\033[F")
        for _ in range(num):
            print('\033[F', file=self.output, end='')

        # print the progress bar
        # self.run()

    def __after_percent_step__(self):
        if self.percent != 0:
            self.cursor_up()
        self.run()

    def run(self):
        size = int(self.width * self.percent)

        args = {
            'bar': '[' + self.SYMBOL * size + ' ' * (self.width - size) + ']',
            'current': self.current,
            'total': self.total,
            'percent': self.percent * 100,
            'remaining': self.total - self.current,
            'title': self.title,
        }

        # print(self.fmt % args, file=self.output, end="\n")
        print(self.fmt % args, file=self.output)

    def done(self):
        args = {
            'bar': '[' + self.SYMBOL * self.width + ']',
            'current': self.total,
            'total': self.total,
            'percent': 100.0,
            'remaining': 0,
            'title': self.title,
        }
        print(self.fmt % args, file=self.output)


class TqdmProgress(BaseProgress):
    def __init__(self, total: int, title: str = ''):
        super().__init__(total)
        is_tty = sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else False
        self.pbar = tqdm(
            total=total,
            desc=title,
            unit='frame',
            dynamic_ncols=is_tty,
            file=sys.stdout if is_tty else sys.stderr,
            mininterval=0.1,
            ascii=not is_tty,
        )

    def __after_percent_step__(self):
        self.pbar.n = self._current
        self.pbar.refresh()

    def done(self):
        self.pbar.n = self.total
        self.pbar.refresh()
        self.pbar.close()


class MediaStateProgress(BaseProgress):
    def __init__(self, total: int, model: Media):
        super().__init__(total)
        self.model = model

    def __after_percent_step__(self):
        self.run()

    def run(self):
        self.model.update_state('compress', self.percent)


if __name__ == '__main__':
    import time

    print(StdoutProgress)
    length = 1000
    stdout_progress = StdoutProgress(length, fmt=StdoutProgress.FULL)
    print(stdout_progress)
    model = Media.get_or_create(**{'md5': 'test', 'title': 'test', 'dirname': 'test'})
    # print(model.__dict__)
    media_progress = MediaStateProgress(length, model)
    # print(media_progress)
    for i in range(length + 1):
        # print(i)
        stdout_progress.current = i
        media_progress.current = i
        # print(i)
        time.sleep(0.1)
    result = model.delete()
    print(result)
