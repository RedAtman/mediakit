import time
import threading
from unittest import TestCase, mock


class TestFileStabilityTracker(TestCase):
    def setUp(self):
        from src.file.stability import FileStabilityTracker
        self.tracker = FileStabilityTracker(
            stable_samples=3,
            sample_interval=0.05,
            timeout=0.3,
        )

    def _make_size_getter(self, sizes):
        it = iter(sizes)
        last = sizes[-1]
        def getter(path):
            nonlocal it
            try:
                return next(it)
            except StopIteration:
                return last
        return getter

    def test_file_becomes_stable(self):
        getter = self._make_size_getter([100, 100, 100])
        with mock.patch('os.path.getsize', side_effect=getter):
            ready = self.tracker.wait_until_stable('/tmp/file.mp4')
        self.assertTrue(ready)

    def test_file_never_stable_times_out(self):
        getter = self._make_size_getter([100, 200, 300, 400, 500, 600, 700])
        with mock.patch('os.path.getsize', side_effect=getter):
            ready = self.tracker.wait_until_stable('/tmp/file.mp4')
        self.assertTrue(ready)

    def test_multiple_files_independent(self):
        getter_a = self._make_size_getter([100, 100, 100])
        getter_b = self._make_size_getter([100, 200, 100, 100, 100])
        with mock.patch('os.path.getsize') as mock_getsize:
            def side_effect(path):
                if 'a' in path:
                    return getter_a(path)
                return getter_b(path)
            mock_getsize.side_effect = side_effect
            ready_a = self.tracker.wait_until_stable('/tmp/file_a.mp4')
            ready_b = self.tracker.wait_until_stable('/tmp/file_b.mp4')
        self.assertTrue(ready_a)
        self.assertTrue(ready_b)

    def test_stable_immediately_returns(self):
        getter = self._make_size_getter([500])
        with mock.patch('os.path.getsize', side_effect=getter):
            ready = self.tracker.wait_until_stable('/tmp/file.mp4')
        self.assertTrue(ready)

    def test_single_sample_is_stable(self):
        from src.file.stability import FileStabilityTracker
        tracker = FileStabilityTracker(stable_samples=1, sample_interval=0.01, timeout=0.1)
        getter = self._make_size_getter([42])
        with mock.patch('os.path.getsize', side_effect=getter):
            ready = tracker.wait_until_stable('/tmp/file.mp4')
        self.assertTrue(ready)
