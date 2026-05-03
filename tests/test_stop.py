import os
import signal
from pathlib import Path
from unittest import TestCase, mock


class TestStopCommand(TestCase):
    def setUp(self):
        self.pid_dir = Path.home() / '.mediakit'
        self.pid_path = self.pid_dir / 'daemon.pid'
        self.pid_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.pid_path.exists():
            self.pid_path.unlink()
        try:
            self.pid_dir.rmdir()
        except OSError:
            pass

    def test_stop_sends_sigterm_by_default(self):
        self.pid_path.write_text('99999')
        with mock.patch('src.schedulers.folder._os.kill') as mock_kill:
            from src.schedulers.folder import _stop
            _stop(force=False)
            self.assertEqual(mock_kill.call_count, 2)
            mock_kill.assert_has_calls([
                mock.call(99999, 0),
                mock.call(99999, signal.SIGTERM),
            ])

    def test_stop_force_sends_sigkill_to_pgroup(self):
        self.pid_path.write_text('99999')
        with mock.patch('src.schedulers.folder._os.kill') as mock_kill:
            with mock.patch('src.schedulers.folder._os.getpgid', return_value=88888):
                with mock.patch('src.schedulers.folder._os.killpg') as mock_killpg:
                    from src.schedulers.folder import _stop
                    _stop(force=True)
                    mock_kill.assert_called_once_with(99999, 0)
                    mock_killpg.assert_called_once_with(88888, signal.SIGKILL)

    def test_stop_no_pid_file_reports_no_daemon(self):
        if self.pid_path.exists():
            self.pid_path.unlink()
        with mock.patch('src.schedulers.folder.logger') as mock_log:
            from src.schedulers.folder import _stop
            _stop(force=False)
            mock_log.info.assert_any_call('No running daemon found.')

    def test_stop_stale_pid_cleans_up_and_reports(self):
        self.pid_path.write_text('99999')
        with mock.patch('src.schedulers.folder._os.kill', side_effect=ProcessLookupError):
            with mock.patch('src.schedulers.folder.logger') as mock_log:
                from src.schedulers.folder import _stop
                _stop(force=False)
                mock_log.info.assert_any_call(
                    'No running daemon found (stale PID file).'
                )
                self.assertFalse(self.pid_path.exists())

    def test_stop_stale_pid_permission_error(self):
        self.pid_path.write_text('99999')
        with mock.patch('src.schedulers.folder._os.kill', side_effect=PermissionError):
            with mock.patch('src.schedulers.folder.logger') as mock_log:
                from src.schedulers.folder import _stop
                _stop(force=False)
                mock_log.warning.assert_called_once()
                self.assertIn(
                    'Permission denied', mock_log.warning.call_args[0][0]
                )

    def test_stop_is_exported(self):
        from src.schedulers import folder
        self.assertTrue(hasattr(folder, 'stop'))
        self.assertTrue(hasattr(folder.stop, 'core'))
        self.assertTrue(callable(folder.stop.core))


class TestStopCli(TestCase):
    def test_stop_action_is_valid(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['stop'])
        self.assertEqual(kwargs.action, 'stop')

    def test_stop_force_flag_long(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['stop', '--force'])
        self.assertTrue(kwargs.force)

    def test_stop_force_defaults_to_false(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['stop'])
        self.assertFalse(kwargs.force)


class TestWatcherPidFile(TestCase):
    def setUp(self):
        self.patchers = [
            mock.patch('src.schedulers.watcher.Observer'),
            mock.patch('src.schedulers.watcher.DebounceBuffer'),
            mock.patch('src.schedulers.watcher.FileStabilityTracker'),
            mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()
        pid_path = Path.home() / '.mediakit' / 'daemon.pid'
        if pid_path.exists():
            pid_path.unlink()

    def test_watcher_writes_and_cleans_up_pid(self):
        from src.schedulers.watcher import WatcherScheduler
        scheduler = WatcherScheduler()
        scheduler._setup_observer = mock.Mock()
        scheduler._feed_existing = mock.Mock()
        scheduler._run_event_loop = mock.Mock()
        with mock.patch.object(scheduler, '_write_pid_file') as mock_write:
            with mock.patch.object(scheduler, '_cleanup_pid_file') as mock_cleanup:
                scheduler.core(
                    folder='/tmp/media', type='video', max_workers=2,
                    cpu_limit=None, no_scan_existing=True, no_recursive=True,
                )
                mock_write.assert_called_once()
                mock_cleanup.assert_called_once()

    def test_cleanup_on_exception_in_event_loop(self):
        from src.schedulers.watcher import WatcherScheduler
        scheduler = WatcherScheduler()
        scheduler._setup_observer = mock.Mock()
        scheduler._feed_existing = mock.Mock()
        scheduler._run_event_loop = mock.Mock(side_effect=RuntimeError('boom'))
        with mock.patch.object(scheduler, '_write_pid_file'):
            with mock.patch.object(scheduler, '_cleanup_pid_file') as mock_cleanup:
                with self.assertRaises(RuntimeError):
                    scheduler.core(
                        folder='/tmp/media', type='video', max_workers=2,
                        cpu_limit=None, no_scan_existing=True, no_recursive=True,
                    )
                mock_cleanup.assert_called_once()

    def test_write_pid_file_creates_file(self):
        from src.schedulers.watcher import WatcherScheduler
        scheduler = WatcherScheduler()
        pid_path = Path.home() / '.mediakit' / 'daemon.pid'
        if pid_path.exists():
            pid_path.unlink()
        scheduler._write_pid_file()
        self.assertTrue(pid_path.exists())
        self.assertEqual(int(pid_path.read_text().strip()), os.getpid())
        pid_path.unlink()

    def test_cleanup_pid_file_removes_file(self):
        pid_path = Path.home() / '.mediakit' / 'daemon.pid'
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(os.getpid()))
        from src.schedulers.watcher import WatcherScheduler
        WatcherScheduler._cleanup_pid_file()
        self.assertFalse(pid_path.exists())

    def test_ensure_pid_dir_creates_directory(self):
        import shutil
        pid_dir = Path.home() / '.mediakit'
        if pid_dir.exists():
            shutil.rmtree(str(pid_dir))
        from src.schedulers.watcher import WatcherScheduler
        result = WatcherScheduler._ensure_pid_dir()
        self.assertTrue(pid_dir.exists())
        self.assertTrue(pid_dir.is_dir())
        self.assertEqual(result, str(pid_dir))

    def test_ensure_pid_dir_is_idempotent(self):
        from src.schedulers.watcher import WatcherScheduler
        first = WatcherScheduler._ensure_pid_dir()
        second = WatcherScheduler._ensure_pid_dir()
        self.assertEqual(first, second)


class TestWatcherInflightTracking(TestCase):
    def setUp(self):
        self.patchers = [
            mock.patch('src.schedulers.watcher.Observer'),
            mock.patch('src.schedulers.watcher.DebounceBuffer'),
            mock.patch('src.schedulers.watcher.FileStabilityTracker'),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    def test_inflight_event_set_during_flush(self):
        from src.schedulers.watcher import WatcherScheduler
        scheduler = WatcherScheduler()
        self.assertFalse(scheduler._inflight_batch.is_set())
        with mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True):
            with mock.patch('src.schedulers.watcher.Folder'):
                scheduler._flush_callback(
                    ['/tmp/media/file.mp4'], 'video', 2
                )
        self.assertFalse(scheduler._inflight_batch.is_set())

    def test_inflight_event_cleared_on_flush_error(self):
        from src.schedulers.watcher import WatcherScheduler
        scheduler = WatcherScheduler()
        with mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True):
            with mock.patch(
                'src.schedulers.watcher.Folder',
                side_effect=RuntimeError('boom'),
            ):
                with self.assertRaises(RuntimeError):
                    scheduler._flush_callback(
                        ['/tmp/media/file.mp4'], 'video', 2
                    )
        self.assertFalse(scheduler._inflight_batch.is_set())

    def test_signal_handler_waits_for_inflight(self):
        from src.schedulers.watcher import WatcherScheduler
        scheduler = WatcherScheduler()
        scheduler._inflight_batch.set()
        scheduler.observer = mock.Mock()
        scheduler._signal_handler(signal.SIGTERM, None)
        self.assertTrue(scheduler._stop_event.is_set())

    def test_signal_handler_skips_wait_when_no_inflight(self):
        from src.schedulers.watcher import WatcherScheduler
        scheduler = WatcherScheduler()
        scheduler._inflight_batch.clear()
        scheduler.observer = mock.Mock()
        scheduler._signal_handler(signal.SIGTERM, None)
        self.assertTrue(scheduler._stop_event.is_set())
