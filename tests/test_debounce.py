import time
import threading
from unittest import TestCase


class TestDebounceBuffer(TestCase):
    def setUp(self):
        from src.file.debounce import DebounceBuffer
        self.flushed = []
        def flush_callback(paths):
            self.flushed.append(list(paths))
        self.buffer = DebounceBuffer(callback=flush_callback, calm_period=0.1)

    def tearDown(self):
        self.buffer.stop()

    def test_add_single_path_then_flush(self):
        self.buffer.add('/tmp/file1.mp4')
        time.sleep(0.3)
        self.assertEqual(len(self.flushed), 1)
        self.assertIn('/tmp/file1.mp4', self.flushed[0])

    def test_dedup_same_path(self):
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file1.mp4')
        time.sleep(0.3)
        self.assertEqual(len(self.flushed), 1)
        self.assertEqual(len(self.flushed[0]), 1)

    def test_multiple_paths_batched(self):
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.add('/tmp/file2.mp4')
        self.buffer.add('/tmp/file3.mp4')
        time.sleep(0.3)
        self.assertEqual(len(self.flushed), 1)
        self.assertEqual(len(self.flushed[0]), 3)

    def test_burst_resets_timer(self):
        self.buffer.add('/tmp/file1.mp4')
        time.sleep(0.05)
        self.buffer.add('/tmp/file2.mp4')
        time.sleep(0.05)
        self.buffer.add('/tmp/file3.mp4')
        time.sleep(0.3)
        self.assertEqual(len(self.flushed), 1)
        self.assertEqual(len(self.flushed[0]), 3)

    def test_multiple_flush_batches(self):
        self.buffer.add('/tmp/file1.mp4')
        time.sleep(0.3)
        self.buffer.add('/tmp/file2.mp4')
        time.sleep(0.3)
        self.assertEqual(len(self.flushed), 2)
        self.assertEqual(self.flushed[0], ['/tmp/file1.mp4'])
        self.assertEqual(self.flushed[1], ['/tmp/file2.mp4'])

    def test_max_flush_interval(self):
        from src.file.debounce import DebounceBuffer
        flushed_batches = []
        def collecting_callback(paths):
            flushed_batches.append(list(paths))
        buffer = DebounceBuffer(callback=collecting_callback, calm_period=1.0, max_flush_interval=0.2)
        buffer.add('/tmp/file1.mp4')
        buffer.add('/tmp/file2.mp4')
        time.sleep(0.4)
        buffer.stop()
        self.assertGreaterEqual(len(flushed_batches), 1)
        paths = []
        for batch in flushed_batches:
            paths.extend(batch)
        self.assertIn('/tmp/file1.mp4', paths)
        self.assertIn('/tmp/file2.mp4', paths)

    def test_flush_empty_buffer_does_nothing(self):
        self.buffer._flush()
        self.assertEqual(len(self.flushed), 0)

    def test_stop_cancels_timer(self):
        self.buffer.add('/tmp/file1.mp4')
        self.buffer.stop()
        time.sleep(0.3)
        self.assertEqual(len(self.flushed), 0)
