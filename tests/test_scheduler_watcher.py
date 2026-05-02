import signal
import threading
from unittest import TestCase, mock


class TestWatcherScheduler(TestCase):
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

    def test_core_attribute_exists(self):
        self.assertTrue(hasattr(self.scheduler, 'core'))
        self.assertTrue(callable(self.scheduler.core))

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
        self.assertEqual(len(call_args[0]), 4)
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
        from watchdog.events import FileSystemEvent
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        handler.stability_tracker.wait_until_stable.return_value = True
        dir_event = FileSystemEvent('/tmp/media/subdir')
        dir_event.is_directory = True
        dir_event.event_type = 'created'
        handler.dispatch(dir_event)
        handler.debounce_buffer.add.assert_not_called()

    def test_on_created_processes_file(self):
        from watchdog.events import FileSystemEvent
        from src.schedulers.watcher import _WatchEventHandler
        handler = _WatchEventHandler(mock.Mock(), mock.Mock())
        handler.debounce_buffer = mock.Mock()
        handler.stability_tracker = mock.Mock()
        handler.stability_tracker.wait_until_stable.return_value = True
        file_event = FileSystemEvent('/tmp/media/file.mp4')
        file_event.is_directory = False
        file_event.event_type = 'created'
        handler.dispatch(file_event)
        handler.stability_tracker.wait_until_stable.assert_called_once_with('/tmp/media/file.mp4')
        handler.debounce_buffer.add.assert_called_once_with('/tmp/media/file.mp4')

    def test_batch_callback_soft_removes_on_success(self):
        from concurrent.futures import Future
        from src.schedulers.watcher import _batch_callback
        from utils.response import Result, ResultStatus
        future = Future()
        future.set_result(Result(code=ResultStatus.SUCCESS, data={'media': mock.Mock(path='/tmp/file.mp4')}))
        with mock.patch('src.schedulers.watcher.file.soft_remove') as mock_remove:
            _batch_callback(future)
            mock_remove.assert_called_once_with('/tmp/file.mp4')

    def test_batch_callback_does_not_remove_on_failure(self):
        from concurrent.futures import Future
        from src.schedulers.watcher import _batch_callback
        from utils.response import Result, ResultStatus
        future = Future()
        future.set_result(Result(code=ResultStatus.FAILED, data={'media': mock.Mock(path='/tmp/file.mp4')}))
        with mock.patch('src.schedulers.watcher.file.soft_remove') as mock_remove:
            _batch_callback(future)
            mock_remove.assert_not_called()
