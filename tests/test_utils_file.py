import hashlib
import logging
import os
import resource
import shutil
import sys
import tempfile
from unittest import TestCase, mock

from utils import file as file_module

logger = logging.getLogger()


def peak_rss_mb() -> float:
    """ru_maxrss 单位随平台不同: macOS 是字节, Linux 是 KB."""
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024) if sys.platform == 'darwin' else value / 1024


class TestCalculateMd5(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write(self, name: str, payload: bytes) -> str:
        path = os.path.join(self.temp_dir, name)
        with open(path, 'wb') as fd:
            fd.write(payload)
        return path

    def test_matches_hashlib_on_small_file(self):
        payload = b'mediakit md5 test'
        path = self._write('small.bin', payload)

        self.assertEqual(file_module.calculate_md5(path), hashlib.md5(payload).hexdigest())

    def test_hashes_across_multiple_chunks(self):
        """大于分块大小时必须逐块喂给 hashlib, 而不是整读."""
        payload = bytes(range(256)) * 10
        path = self._write('multi.bin', payload)

        with mock.patch.object(file_module, 'MD5_CHUNK_SIZE', 7):
            self.assertEqual(file_module.calculate_md5(path), hashlib.md5(payload).hexdigest())

    def test_does_not_hold_the_whole_file_in_memory(self):
        """整文件 read() 会让峰值 RSS 至少等于文件大小, 扫描大媒体库时能冲到 GB 级
        (实测 512MB 文件把峰值从 19MB 抬到 532MB). 分块实现只多几 MB.
        """
        payload = b'\0' * (32 * 1024 * 1024)
        path = self._write('big.bin', payload)

        before = peak_rss_mb()
        file_module.calculate_md5(path)
        grown = peak_rss_mb() - before

        self.assertLess(grown, 16, f'peak RSS grew by {grown:.0f}MB - looks like a whole-file read')
