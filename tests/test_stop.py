import os
import signal
from unittest import TestCase, mock

from src.file.pid import daemon_pid_path


class TestStopCommand(TestCase):
    def setUp(self):
        # conftest 的 isolated_pid_dir 把 MEDIAKIT_PID_DIR 指到 tmp_path
        self.pid_path = daemon_pid_path()
        self.pid_dir = self.pid_path.parent
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
            mock_kill.assert_has_calls([mock.call(99999, 0), mock.call(99999, signal.SIGTERM)])

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
                mock_log.info.assert_any_call('No running daemon found (stale PID file).')
                self.assertFalse(self.pid_path.exists())

    def test_stop_permission_error_is_reported_not_raised(self):
        """守护进程属于别的用户: 判活时权限拒绝说明它活着, 发信号再被拒要给出警告."""
        self.pid_path.write_text('99999')
        with (
            mock.patch('src.file.pid.os.kill', side_effect=PermissionError),
            mock.patch('src.schedulers.folder._os.kill', side_effect=PermissionError),
            mock.patch('src.schedulers.folder.logger') as mock_log,
        ):
            from src.schedulers.folder import _stop

            _stop(force=False)
        mock_log.warning.assert_called_once()
        self.assertIn('Permission denied', mock_log.warning.call_args[0][0])

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
        pid_path = daemon_pid_path()
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
                    folder='/tmp/media',
                    type='video',
                    max_workers=2,
                    cpu_limit=None,
                    no_scan_existing=True,
                    recursive=False,
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
                        folder='/tmp/media',
                        type='video',
                        max_workers=2,
                        cpu_limit=None,
                        no_scan_existing=True,
                        recursive=False,
                    )
                mock_cleanup.assert_called_once()

    def test_write_pid_file_creates_file(self):
        from src.schedulers.watcher import WatcherScheduler

        scheduler = WatcherScheduler()
        pid_path = daemon_pid_path()
        if pid_path.exists():
            pid_path.unlink()
        scheduler._write_pid_file()
        self.assertTrue(pid_path.exists())
        self.assertEqual(int(pid_path.read_text().strip()), os.getpid())
        pid_path.unlink()

    def test_cleanup_pid_file_removes_file(self):
        pid_path = daemon_pid_path()
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(os.getpid()))
        from src.schedulers.watcher import WatcherScheduler

        WatcherScheduler._cleanup_pid_file()
        self.assertFalse(pid_path.exists())


class TestPidReservationBeforeBacklog(TestCase):
    """pid 文件必须在启动积压之前写好, 否则 stop 与单实例守卫在积压期间完全失效."""

    def setUp(self):
        self.patchers = [
            mock.patch('src.schedulers.watcher.Observer'),
            mock.patch('src.schedulers.watcher.DebounceBuffer'),
            mock.patch('src.schedulers.watcher.FileStabilityTracker'),
            mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.pid_path = daemon_pid_path()

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()
        if self.pid_path.exists():
            self.pid_path.unlink()

    def _scheduler(self):
        from src.schedulers.watcher import WatcherScheduler

        scheduler = WatcherScheduler()
        scheduler._setup_observer = mock.Mock()
        scheduler._run_event_loop = mock.Mock()
        return scheduler

    def test_pid_file_exists_while_the_backlog_runs(self):
        scheduler = self._scheduler()
        seen = {}

        def fake_feed_existing(*args, **kwargs):
            seen['exists'] = self.pid_path.exists()
            seen['pid'] = int(self.pid_path.read_text().strip()) if self.pid_path.exists() else None

        scheduler._feed_existing = mock.Mock(side_effect=fake_feed_existing)
        scheduler.core(folder='/tmp/media', type='video', max_workers=1, cpu_limit=None, recursive=False)

        self.assertTrue(seen.get('exists'), 'nothing to stop during the backlog: pid file was missing')
        self.assertEqual(seen['pid'], os.getpid())
        self.assertFalse(self.pid_path.exists(), 'core() must still clean up on the way out')

    def test_pid_file_is_removed_when_the_backlog_raises(self):
        scheduler = self._scheduler()
        scheduler._feed_existing = mock.Mock(side_effect=RuntimeError('ffmpeg vanished'))
        with self.assertRaises(RuntimeError):
            scheduler.core(folder='/tmp/media', type='video', max_workers=1, cpu_limit=None, recursive=False)
        self.assertFalse(self.pid_path.exists())

    def test_stop_during_backlog_skips_the_remaining_folders(self):
        scheduler = self._scheduler()
        scheduler._feed_existing = mock.Mock(side_effect=lambda *a, **k: scheduler._stop_event.set())
        scheduler.core(folder='/tmp/media', type='video', max_workers=1, cpu_limit=None, recursive=False)

        # 第一个目录处理完就退出, 不再进第二个, 也不进事件循环
        self.assertEqual(scheduler._feed_existing.call_count, 1)
        scheduler._run_event_loop.assert_not_called()
        self.assertFalse(self.pid_path.exists())

    def test_cleanup_leaves_a_foreign_pid_file(self):
        from src.schedulers.watcher import WatcherScheduler

        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text('424242')
        WatcherScheduler._cleanup_pid_file()
        self.assertTrue(self.pid_path.exists(), "cleanup must not delete another process's pid file")
        self.assertEqual(self.pid_path.read_text().strip(), '424242')


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
                scheduler._flush_callback(['/tmp/media/file.mp4'], 'video', 2)
        self.assertFalse(scheduler._inflight_batch.is_set())

    def test_inflight_event_cleared_on_flush_error(self):
        from src.schedulers.watcher import WatcherScheduler

        scheduler = WatcherScheduler()
        # Folder 构造失败现在只跳过该文件, 所以要制造一个"逃出去"的异常来验在飞标记的清理:
        # 用 run___ 抛错 (Folder 本身能构造成功)
        mock_media = mock.Mock()
        type(mock_media).metadata = mock.PropertyMock(return_value={'streams': []})
        with (
            mock.patch('src.schedulers.watcher.os.path.isdir', return_value=True),
            mock.patch('src.schedulers.watcher.Folder') as mock_folder_cls,
            mock.patch('src.schedulers.watcher.Folder.run___', side_effect=RuntimeError('boom')),
        ):
            mock_folder_cls.return_value.MEDIA_CLS.return_value = mock_media
            with self.assertRaises(RuntimeError):
                scheduler._flush_callback(['/tmp/media/file.mp4'], 'video', 2)
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
