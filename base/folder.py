import functools
import os

__all__ = [
    'BaseFolder',
]


class BaseFolder:

    def __init__(self, path: str):
        path = path.strip()
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found at path: {path}')
        if not os.path.isdir(rf'{path}'):
            raise TypeError(f'Path is not a folder: {path}')
        self.path = path
        self.abspath = os.path.abspath(path)

    @functools.cached_property
    def files(self):
        return self.get_files(self.path)

    @staticmethod
    def get_files(path: str):
        return (os.path.abspath(os.path.join(path, file)) for file in os.listdir(path))
