import logging
import os
import signal
import tempfile
from unittest import TestCase, mock

logger = logging.getLogger()


class TestFileOverrideIntegration(TestCase):
    """Integration tests for file-based CPU override.

    override 文件路径可注入, 因为默认的 /tmp/mediakit_cpu_* 是进程间共享的:
    其他 CPULimiterCoordinator 实例的监视线程每 2s 会扫描并删除匹配文件,
    测试刚创建的文件可能在断言前就被别人删掉 (CI 上偶发)。
    """

    def test_file_override_detected_and_target_updated(self):
        """File override changes _manual_target and propagates to throttlers."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        override_dir = tempfile.mkdtemp()
        coord = CPULimiterCoordinator(
            default_limit=100, auto_mode=True, file_override_pattern=os.path.join(override_dir, 'mediakit_cpu_*')
        )
        coord._stop_monitor()

        filepath = os.path.join(override_dir, 'mediakit_cpu_7')
        try:
            # Create the file
            open(filepath, 'w').close()
            self.assertTrue(os.path.exists(filepath))

            # Scan should find and process it
            coord._scan_file_override()

            # File should be removed after processing
            self.assertFalse(os.path.exists(filepath))

            # Manual override should be active with target 7
            self.assertTrue(coord._manual_override_active)
            self.assertEqual(coord._manual_target, 7)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_file_override_propagates_to_existing_throttlers(self):
        """File override updates the target of already-running throttlers."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        override_dir = tempfile.mkdtemp()
        coord = CPULimiterCoordinator(
            default_limit=100, auto_mode=False, file_override_pattern=os.path.join(override_dir, 'mediakit_cpu_*')
        )
        coord._stop_monitor()

        # Attach throttlers (simulating ffmpeg start)
        coord.attach(9998)
        coord.attach(9997)

        # Now simulate file override: touch mediakit_cpu_3 in the private dir
        filepath = os.path.join(override_dir, 'mediakit_cpu_3')
        try:
            open(filepath, 'w').close()
            coord._scan_file_override()

            # Manual target should be updated
            self.assertEqual(coord._manual_target, 3)

            # Each throttler should have target = max(int(3/2), 1) = 1
            # (manual override mode: no MIN_PER_WORKER floor)
            info_1 = coord._throttlers[9998]
            info_2 = coord._throttlers[9997]
            self.assertEqual(info_1['throttler'].target, 1)
            self.assertEqual(info_2['throttler'].target, 1)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

        coord.detach(9998)
        coord.detach(9997)

    @mock.patch('os.kill')
    def test_throttler_sends_sigstop_after_override_to_low_value(self, mock_kill):
        """Throttler sends SIGSTOP when target drops from 100 to a low value."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 100)

        # Fill sliding window with high values (simulating 100% CPU)
        throttler._samples.extend([100.0, 100.0, 100.0, 100.0, 100.0])
        throttler._is_stopped_state = False

        # Mock _sample_cpu to return a steady value
        throttler._sample_cpu = mock.Mock(return_value=100.0)

        # Run one cycle at target=100: avg(100) > 100? → No, so no SIGSTOP
        throttler._loop_once()
        mock_kill.assert_not_called()

        # Now change target to 1 (simulating file override)
        throttler.target = 1

        # Fill sliding window again (the append in _loop_once above would have
        # shifted things, but let's set a stable state)
        throttler._samples.extend([50.0, 50.0, 50.0, 50.0])

        # Run one cycle at target=1: avg(50) > 1? → Yes → SIGSTOP!
        throttler._loop_once()

        # Verify SIGSTOP was sent
        mock_kill.assert_called_with(9999, signal.SIGSTOP)
        self.assertTrue(throttler._is_stopped_state)

    @mock.patch('os.kill')
    def test_config_middleware_sets_manual_override(self, mock_kill):
        """_config middleware sets manual override from the default cpu_limit."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._stop_monitor()

        # Simulate what _config does: pop cpu_limit and call set_manual_override
        cpu_limit = 50  # Default from CONFIG.CPU_LIMIT
        if isinstance(cpu_limit, int) and cpu_limit > 0:
            coord.set_manual_override(cpu_limit)

        self.assertTrue(coord._manual_override_active)
        self.assertEqual(coord._manual_target, 50)

        # Now simulate file override from low to high
        filepath = '/tmp/mediakit_cpu_1'
        try:
            open(filepath, 'w').close()
            coord._scan_file_override()
            self.assertEqual(coord._manual_target, 1)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


def _install_private_coordinator(monkeypatch, tmp_path):
    """让 folder.coordinator() 造出来的协调器只扫 tmp_path 下的 override 文件.

    默认 /tmp/mediakit_cpu_* 是进程间共享的, 别人的监视线程会抢着删掉测试文件.
    返回被创建过的协调器列表, 供断言 "到底有没有被建出来".
    """
    from src.schedulers import folder as folder_sched
    from utils.command import CommandExecutor
    from utils.throttle.coordinator import CPULimiterCoordinator

    created = []

    def factory(**kwargs):
        coord = CPULimiterCoordinator(file_override_pattern=str(tmp_path / 'mediakit_cpu_*'), **kwargs)
        created.append(coord)
        return coord

    monkeypatch.setattr(folder_sched, '_coordinator', None)
    monkeypatch.setattr(folder_sched, 'CPULimiterCoordinator', factory)
    monkeypatch.setattr(CommandExecutor, 'coordinator', None, raising=False)
    return created


def test_folder_config_creates_coordinator_without_cpu_limit(monkeypatch, tmp_path):
    """不带 -c 时也必须建出协调器, 否则 /tmp/mediakit_cpu_* 根本没人扫. 回归测试."""
    from src.schedulers.folder import _config
    from utils.command import CommandExecutor

    created = _install_private_coordinator(monkeypatch, tmp_path)
    ctx = mock.MagicMock()
    _config(ctx=ctx)
    ctx.next.assert_called_once()

    assert len(created) == 1, 'no -c must still create the coordinator'
    coord = created[0]
    try:
        # 协调器必须挂到 CommandExecutor 上, 否则 attach() 永远不会被调用
        assert CommandExecutor.coordinator is coord
        # 没用 -c 就不该动预算, 保持 auto 模式
        assert coord._manual_override_active is False
        (tmp_path / 'mediakit_cpu_12').touch()
        coord._scan_file_override()
        assert coord._manual_target == 12
        assert not (tmp_path / 'mediakit_cpu_12').exists()
    finally:
        coord._stop_monitor()


def test_folder_config_applies_cpu_limit(monkeypatch, tmp_path):
    """-c 仍然要立刻变成手动预算 (它只是不再是一切的前提)."""
    from src.schedulers.folder import _config

    created = _install_private_coordinator(monkeypatch, tmp_path)
    _config(cpu_limit='40', ctx=mock.MagicMock())

    assert len(created) == 1
    coord = created[0]
    try:
        assert coord._manual_override_active is True
        assert coord._manual_target == 40
    finally:
        coord._stop_monitor()


def test_watcher_setup_creates_coordinator_without_cpu_limit(monkeypatch, tmp_path):
    """watch 模式同样的一条回归: 不带 -c 也要有协调器在盯 override 文件."""
    from src.schedulers.watcher import WatcherScheduler

    created = _install_private_coordinator(monkeypatch, tmp_path)
    WatcherScheduler._setup_cpu_throttling(object.__new__(WatcherScheduler), None)

    assert len(created) == 1, 'watch mode must create the coordinator too'
    created[0]._stop_monitor()
