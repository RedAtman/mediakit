import logging
import os
import signal
from unittest import TestCase, mock

logger = logging.getLogger()


class TestFileOverrideIntegration(TestCase):
    """Integration tests for file-based CPU override."""

    def test_file_override_detected_and_target_updated(self):
        """File override changes _manual_target and propagates to throttlers."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._stop_monitor()

        filepath = '/tmp/mediakit_cpu_7'
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

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=False)
        coord._stop_monitor()

        # Attach throttlers (simulating ffmpeg start)
        coord.attach(9998)
        coord.attach(9997)

        # Now simulate file override: touch /tmp/mediakit_cpu_3
        filepath = '/tmp/mediakit_cpu_3'
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

    @mock.patch("os.kill")
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

    @mock.patch("os.kill")
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
