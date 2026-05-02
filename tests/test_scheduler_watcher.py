import os
import signal
from unittest import TestCase, mock


class TestWatcherScheduler(TestCase):
    def setUp(self):
        self.patchers = [
            mock.patch('src.schedulers.watcher.Observer'),
            mock.patch('src.schedulers.watcher.DebounceBuffer'),
            mock.patch('src.schedulers.watcher.FileStabilityTracker'),
            mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True),
        ]
        for p in self.patchers:
            p.start()
        from src.schedulers.watcher import WatcherScheduler
        self.scheduler = WatcherScheduler()

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    def test_core_attribute_exists(self):
        self.assertTrue(hasattr(self.scheduler, 'core'))
        self.assertTrue(callable(self.scheduler.core))

    def test_setup_observer_passes_correct_constructor_args(self):
        scheduler = self.scheduler
        scheduler._setup_observer('/tmp/media', False, 'video', 2)
        import src.schedulers.watcher as watcher_module
        watcher_module.DebounceBuffer.assert_called_once_with(
            calm_period=5.0, max_flush_interval=60.0, callback=mock.ANY
        )
        watcher_module.FileStabilityTracker.assert_called_once_with(
            sample_interval=1.0, stable_samples=3, timeout=30.0
        )

    def test_observer_created_with_path_and_recursive(self):
        scheduler = self.scheduler
        scheduler._setup_observer('/tmp/media', False, 'video', 2)
        self.scheduler.observer.schedule.assert_called_once()
        args, kwargs = self.scheduler.observer.schedule.call_args
        handler = args[0]
        watched_path = args[1]
        recursive = kwargs.get('recursive')
        self.assertEqual(watched_path, '/tmp/media')
        self.assertFalse(recursive)
        self.assertTrue(hasattr(handler, 'on_created'))

    def test_core_calls_setup_observer(self):
        scheduler = self.scheduler
        scheduler._setup_observer = mock.Mock()
        scheduler._feed_existing = mock.Mock()
        scheduler._run_event_loop = mock.Mock()
        scheduler.core(folder='/tmp/media', type='video', max_workers=2, cpu_limit=None)
        call_args = scheduler._setup_observer.call_args
        self.assertEqual(call_args[0][0], '/tmp/media')
        self.assertEqual(call_args[0][1], True)
        self.assertEqual(len(call_args[0]), 5)
        self.assertEqual(call_args[0][4], 'compress')
        scheduler._run_event_loop.assert_called_once()

    def test_core_calls_feed_existing_by_default(self):
        scheduler = self.scheduler
        scheduler._setup_observer = mock.Mock()
        scheduler._feed_existing = mock.Mock()
        scheduler._run_event_loop = mock.Mock()
        scheduler.core(folder='/tmp/media', no_scan_existing=False, type='video', max_workers=2, cpu_limit=None)
        scheduler._feed_existing.assert_called_once()

    def test_core_skips_feed_existing_with_flag(self):
        scheduler = self.scheduler
        scheduler._setup_observer = mock.Mock()
        scheduler._feed_existing = mock.Mock()
        scheduler._run_event_loop = mock.Mock()
        scheduler.core(folder='/tmp/media', no_scan_existing=True, type='video', max_workers=2, cpu_limit=None)
        scheduler._feed_existing.assert_not_called()

    def test_observer_is_alive_check_called_in_loop(self):
        scheduler = self.scheduler
        scheduler._setup_observer = mock.Mock()
        scheduler._feed_existing = mock.Mock()
        mock_obs = mock.Mock()
        mock_obs.is_alive.return_value = True
        scheduler.observer = mock_obs
        scheduler._stop_event = mock.Mock()
        scheduler._stop_event.is_set.side_effect = [False, True]
        scheduler._run_event_loop()
        self.assertTrue(mock_obs.is_alive.called)

    def test_observer_restart_on_death(self):
        scheduler = self.scheduler
        scheduler._setup_observer = mock.Mock()
        scheduler._feed_existing = mock.Mock()
        mock_obs = mock.Mock()
        mock_obs.is_alive.side_effect = [False, True]
        mock_obs.start = mock.Mock()
        scheduler.observer = mock_obs
        scheduler._stop_event = mock.Mock()
        scheduler._stop_event.is_set.side_effect = [False, False, True]
        with mock.patch('logging.Logger.warning'):
            scheduler._run_event_loop()
        self.assertEqual(mock_obs.start.call_count, 1)

    def test_signal_handler_sets_stop_event(self):
        scheduler = self.scheduler
        scheduler._stop_event = mock.Mock()
        scheduler.observer = mock.Mock()
        scheduler.task_manager = mock.Mock()
        scheduler._signal_handler(signal.SIGINT, None)
        scheduler._stop_event.set.assert_called_once()

    def test_event_handler_filters_directories(self):
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        handler.stability_tracker.wait_until_stable.return_value = True
        dir_event = self._make_event('/tmp/media/subdir', 'created', is_directory=True)
        handler.dispatch(dir_event)
        handler.debounce_buffer.add.assert_not_called()

    def _make_event(self, path, event_type='created', is_directory=False):
        from watchdog.events import FileSystemEvent
        event = FileSystemEvent(path)
        event.is_directory = is_directory
        event.event_type = event_type
        return event

    def test_on_created_processes_file(self):
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        handler.stability_tracker.wait_until_stable.return_value = True
        event = self._make_event('/tmp/media/file.mp4', 'created')
        handler.dispatch(event)
        handler.stability_tracker.wait_until_stable.assert_called_once_with('/tmp/media/file.mp4')
        handler.debounce_buffer.add.assert_called_once_with('/tmp/media/file.mp4')

    def test_on_modified_processes_file(self):
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        handler.stability_tracker.wait_until_stable.return_value = True
        event = self._make_event('/tmp/media/file.mp4', 'modified')
        handler.dispatch(event)
        handler.stability_tracker.wait_until_stable.assert_called_once_with('/tmp/media/file.mp4')
        handler.debounce_buffer.add.assert_called_once_with('/tmp/media/file.mp4')

    def test_on_moved_uses_dest_path(self):
        from watchdog.events import FileMovedEvent
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        handler.stability_tracker.wait_until_stable.return_value = True
        event = FileMovedEvent('/tmp/temp.mp4', '/tmp/media/file.mp4')
        handler.dispatch(event)
        handler.stability_tracker.wait_until_stable.assert_called_once_with('/tmp/media/file.mp4')
        handler.debounce_buffer.add.assert_called_once_with('/tmp/media/file.mp4')

    def test_skips_output_subdirectory(self):
        from watchdog.events import FileSystemEvent
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        file_event = FileSystemEvent('/tmp/media/_[compress.libx265.slow]/file.mp4')
        file_event.is_directory = False
        file_event.event_type = 'created'
        handler.dispatch(file_event)
        handler.debounce_buffer.add.assert_not_called()

    def test_skips_removed_directory(self):
        from watchdog.events import FileSystemEvent
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        file_event = FileSystemEvent('/tmp/media/.removed/file.mp4')
        file_event.is_directory = False
        file_event.event_type = 'created'
        handler.dispatch(file_event)
        handler.debounce_buffer.add.assert_not_called()

    @mock.patch('src.schedulers.watcher.os.path.exists', return_value=True)
    def test_batch_callback_soft_removes_on_success(self, mock_exists):
        from concurrent.futures import Future
        from src.schedulers.watcher import _batch_callback
        future = Future()
        future.set_result({'media': mock.Mock(path='/tmp/file.mp4'), 'new_file_path': '/tmp/file.mp4'})
        with mock.patch('src.schedulers.watcher.file.soft_remove') as mock_remove:
            _batch_callback(future)
            mock_remove.assert_called_once_with('/tmp/file.mp4')

    @mock.patch('src.schedulers.watcher.os.path.exists', return_value=False)
    def test_batch_callback_does_not_remove_when_output_missing(self, mock_exists):
        from concurrent.futures import Future
        from src.schedulers.watcher import _batch_callback
        future = Future()
        future.set_result({'media': mock.Mock(path='/tmp/file.mp4'), 'new_file_path': '/tmp/file.mp4'})
        with mock.patch('src.schedulers.watcher.file.soft_remove') as mock_remove:
            _batch_callback(future)
            mock_remove.assert_not_called()

    def test_batch_callback_skips_non_dict_result(self):
        from concurrent.futures import Future
        from src.schedulers.watcher import _batch_callback
        future = Future()
        future.set_result(None)
        with mock.patch('src.schedulers.watcher.file.soft_remove') as mock_remove:
            _batch_callback(future)
            mock_remove.assert_not_called()


class TestWatcherMultiFolder(TestCase):
    def setUp(self):
        self.patchers = [
            mock.patch('src.schedulers.watcher.Observer'),
            mock.patch('src.schedulers.watcher.DebounceBuffer'),
            mock.patch('src.schedulers.watcher.FileStabilityTracker'),
        ]
        for p in self.patchers:
            p.start()
        from src.schedulers.watcher import WatcherScheduler
        self.scheduler = WatcherScheduler()

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    @mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True)
    def test_multi_observer_schedules_each_path(self, mock_isdir):
        s = self.scheduler
        s._setup_multi_observer(['/a', '/b'], False, 'video', 2)
        s.observer.schedule.assert_has_calls([
            mock.call(mock.ANY, '/a', recursive=False),
            mock.call(mock.ANY, '/b', recursive=False),
        ])
        self.assertEqual(s.observer.schedule.call_count, 2)

    @mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True)
    def test_core_with_folder_file_calls_multi_observer(self, mock_isdir):
        s = self.scheduler
        s._feed_existing = mock.Mock()
        s._run_event_loop = mock.Mock()
        with mock.patch('src.schedulers.watcher._parse_folder_file', return_value=['/a', '/b']):
            s.core(folder_file='/p.txt', type='video', max_workers=2, cpu_limit=None,
                   no_scan_existing=True, no_recursive=False)
        s.observer.schedule.assert_has_calls([
            mock.call(mock.ANY, '/a', recursive=True),
            mock.call(mock.ANY, '/b', recursive=True),
        ])
        self.assertEqual(s.observer.schedule.call_count, 2)

    @mock.patch('src.schedulers.watcher.os.path.isdir', side_effect=lambda p: p == '/a')
    def test_nonexistent_paths_skipped_with_warning(self, mock_isdir):
        s = self.scheduler
        s._run_event_loop = mock.Mock()
        with mock.patch('src.schedulers.watcher._parse_folder_file', return_value=['/a', '/nonexistent']):
            with mock.patch('src.schedulers.watcher.logger.warning') as mock_warn:
                s.core(folder_file='/p.txt', type='video', max_workers=2, cpu_limit=None,
                       no_scan_existing=True, no_recursive=True)
                mock_warn.assert_called_once()
                self.assertIn('/nonexistent', mock_warn.call_args[0][1])
        s.observer.schedule.assert_called_once_with(mock.ANY, '/a', recursive=False)

    @mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True)
    def test_core_uses_single_setup_when_no_folder_file(self, mock_isdir):
        s = self.scheduler
        s._setup_observer = mock.Mock()
        s._feed_existing = mock.Mock()
        s._run_event_loop = mock.Mock()
        s.core(folder='/tmp/media', type='video', max_workers=2, cpu_limit=None,
               no_scan_existing=True, no_recursive=False)
        s._setup_observer.assert_called_once_with('/tmp/media', True, 'video', 2, 'compress')


class TestParseFolderFile(TestCase):
    def _write_tmp(self, content):
        import tempfile
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_skips_comments_and_blanks(self):
        from src.schedulers.watcher import _parse_folder_file
        path = self._write_tmp('# comment\n/media/videos\n\n/photos\n  \n')
        try:
            self.assertEqual(_parse_folder_file(path), ['/media/videos', '/photos'])
        finally:
            os.unlink(path)

    def test_strips_whitespace(self):
        from src.schedulers.watcher import _parse_folder_file
        path = self._write_tmp('  /media/videos  \n\t/photos\n')
        try:
            self.assertEqual(_parse_folder_file(path), ['/media/videos', '/photos'])
        finally:
            os.unlink(path)

    def test_all_comments_returns_empty(self):
        from src.schedulers.watcher import _parse_folder_file
        path = self._write_tmp('# a\n# b\n')
        try:
            self.assertEqual(_parse_folder_file(path), [])
        finally:
            os.unlink(path)

    def test_empty_file_returns_empty(self):
        from src.schedulers.watcher import _parse_folder_file
        path = self._write_tmp('')
        try:
            self.assertEqual(_parse_folder_file(path), [])
        finally:
            os.unlink(path)
