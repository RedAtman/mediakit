import mimetypes
import re
import sys

from logger import logger  # pylint: disable=unused-import

__all__ = [
    'Dict2Obj',
    'is_media',
    'ProgressBar',
    'loading_bar',
    'progressbar',
]


# class Dict2Obj:
#     '''Convert dict to object recursively.'''
#     def __init__(self, data):
#         for name, value in data.items():
#             setattr(self, name, self.__wrap(value))

#     def __wrap(self, value):
#         if isinstance(value, (tuple, list, set, frozenset)):
#             return type(value)([self.__wrap(v) for v in value])
#         return Dict2Obj(value) if isinstance(value, dict) else value

#     def _dict(self):
#         return {k: v._dict() if isinstance(v, Dict2Obj) else v
#                 for k, v in self.__dict__.items()}


class Dict2Obj(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self


mimetypes.init()


def is_media(file):
    '''Check if the file is a media file.'''
    mime_start = mimetypes.guess_type(file)[0]
    if mime_start is not None:
        mime_start = mime_start.split('/')[0]
        if mime_start in [
            # 'audio',
            'video',
        ]:
            return True
    return False


class ProgressBar:
    '''Print a progress bar to `sys.stderr`.

    Arguments:
        total {[int]} -- [Total count]
        title {[str]} -- [Title of the progress bar] (default: {'Progress'})
        width {[int]} -- [Width of the progress bar] (default: {40})
        fmt {[str]} -- [Format of the progress bar] (default: {DEFAULT})
        output {[sys.stderr]} -- [Output of the progress bar] (default: {sys.stderr})

    Usage:
        progress = ProgressBar(100)
        for i in range(0, 100):
            progress.current = i
            time.sleep(.1)
        progress.done()
    Example:
        Progress: [##########          ] 50%
    '''
    # TITLE = 'Progress'
    SYMBOL = '█'
    assert len(SYMBOL) == 1
    DEFAULT = '%(title)s: %(bar)s %(percent)3d%%'
    FULL = '%(bar)s %(current)d/%(total)d (%(percent)3d%%) %(remaining)d %(title)s'

    def __init__(self, total, title='Progress', width=40, fmt=DEFAULT, output=sys.stderr):
        self.title = title
        self.total = float(total)
        self.width = width
        self.output = output
        self._current = 0
        self.fmt = re.sub(
            r'(?P<name>%\(.+?\))d',
            rf'\g<name>{len(str(total))}d',
            fmt,
        )

    def __repr__(self) -> str:
        return f'<ProgressBar: {self.title}>'

    # current = property(fget=lambda self: self._current)

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, value):
        self._current = float(value)
        self()

    def __call__(self):
        percent = self.current / float(self.total)
        size = int(self.width * percent)
        remaining = self.total - self.current
        _bar = '[' + self.SYMBOL * size + ' ' * (self.width - size) + ']'

        args = {
            'total': self.total,
            'bar': _bar,
            'current': self.current,
            'percent': percent * 100,
            'remaining': remaining,
            'title': self.title,
        }
        print('\r' + self.fmt % args, file=self.output, end='')

    def done(self):
        self.current = self.total
        print('', file=self.output)

    def parse_current(self, stdout_line: str):
        current = re.findall(r'frame=\s*(\d+)', stdout_line)
        if current:
            current = current[-1]
            self.current = current


def loading_bar(count, total, size):
    '''Use `sys.stdout.write` to print the loading bar.

    Arguments:
        count {[int]} -- [Current count]
        total {[int]} -- [Total count]
        size {[int]} -- [Size of the loading bar]

    Usage:
        for i in range(0, 100):
            loading_bar(i, 100, 2)
            time.sleep(.1)
    Example:
        001/100 [==========] 100%
    '''
    percent = float(count)/float(total) * 100
    sys.stdout.write(
        "\r" + str(int(count)).rjust(3, '0') + "/" + str(int(total)).rjust(3, '0') + ' [' + '=' * \
        int(percent / 10) * size + ' ' * (10 - int(percent / 10)) * size + ']'
    )


def progressbar(count: int) -> None:
    '''Use `sys.stdout.write` to print the progress bar.

    Arguments:
        count {int} -- [Current count]

    Usage:
        for i in progressbar(100):
            time.sleep(0.1)
    Example:
        [##########] - 10/10
    '''
    for current in range(count):
        print(f"[{current * '#'}{(count - 1 - current)*' '}] - {current + current}/{count}", end="\r")
        yield current
    print('\n')
