import glob
import hashlib
import os
import shutil
from typing import Any

__all__ = ['calculate_md5', 'change_file_extension', 'soft_remove']


# 1 MiB 分块: 整文件 read() 会让扫描期峰值 RSS 等于最大文件尺寸
# (实测 512MB 文件把峰值从 19MB 抬到 532MB, 真实媒体库上看到过 9.4GB)
MD5_CHUNK_SIZE = 1024 * 1024


def calculate_md5(file_path: str) -> str:
    """Calculate the MD5 sum of a file, streaming it in chunks."""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(MD5_CHUNK_SIZE), b''):
            md5.update(chunk)
    return md5.hexdigest()


def change_file_extension(folder: str | None = None, old_ext: str | None = None, ext: str | None = None, **kwargs: Any):
    if not folder or not old_ext or not ext:
        raise ValueError('folder, old_ext, ext must be provided')
    # Create a case-insensitive glob pattern: samples/*.[mM][pP][44]
    old_ext_pattern = ''.join([f'[{c.lower()}{c.upper()}]' for c in old_ext])
    pathname_pattern: str = os.path.join(folder, f'*.{old_ext_pattern}')
    result: dict[str, Any] = {}
    for filename in glob.glob(pathname_pattern):
        base = os.path.splitext(filename)[0]
        os.rename(filename, base + f'.{ext}')
        result[filename] = base + f'.{ext}'
    return result


def soft_remove(file_path: str) -> None:
    basedir, filename = os.path.split(file_path)
    remove_folder = os.path.join(basedir, '.removed')
    if not os.path.exists(remove_folder):
        os.makedirs(remove_folder)
    shutil.move(file_path, os.path.join(remove_folder, filename))


if __name__ == '__main__':
    # change_file_extension(folder="samples", old_ext="mp4", ext="avi")
    # soft_remove("samples/zh.mp4")
    print(calculate_md5('README.md'))
