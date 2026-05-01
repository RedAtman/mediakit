import logging
import os
import signal
from unittest import TestCase, main, mock

logger = logging.getLogger()


class TestProcessThrottler(TestCase):
    """Tests for ProcessThrottler."""

    def test_throttler_attaches_to_pid(self):
        """Throttler stores PID, starts as daemon, has stop event."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        self.assertEqual(throttler.pid, 9999)
        self.assertTrue(throttler.daemon)
        self.assertFalse(throttler._stopped.is_set())

    def test_throttler_target_fn_is_called(self):
        """target_fn is called to get current target."""
        from utils.throttle.throttler import ProcessThrottler

        mock_target = mock.Mock(return_value=50)
        throttler = ProcessThrottler(pid=9999, target_fn=mock_target)
        self.assertEqual(throttler.target, 50)
        mock_target.assert_called_once()

    def test_throttler_target_property_dynamic(self):
        """Setting .target overrides target_fn."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 100)
        self.assertEqual(throttler.target, 100)
        throttler.target = 50
        self.assertEqual(throttler.target, 50)

    @mock.patch("os.kill")
    def test_throttler_stop_stops_loop(self, mock_kill):
        """stop() sets stop event."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        self.assertFalse(throttler._stopped.is_set())
        throttler.stop()
        self.assertTrue(throttler._stopped.is_set())

    @mock.patch("os.kill")
    def test_throttler_stops_on_esrch(self, mock_kill):
        """Zombie process (ESRCH) causes throttler to mark zombie."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)

        def zombie_fn():
            throttler.zombie = True
            return 0.0

        throttler._sample_cpu = zombie_fn
        throttler._loop_once()
        self.assertTrue(throttler.zombie)

    @mock.patch("os.kill")
    def test_throttler_sends_sigstop_above_target(self, mock_kill):
        """When window average exceeds target, sends SIGSTOP."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        throttler._samples.extend([60.0, 55.0, 58.0, 62.0, 59.0])
        throttler._is_stopped_state = False
        throttler._sample_cpu = mock.Mock(return_value=59.0)

        throttler._loop_once()

        mock_kill.assert_called_with(9999, signal.SIGSTOP)
        self.assertTrue(throttler._is_stopped_state)

    @mock.patch("os.kill")
    def test_throttler_sends_sigcont_below_target(self, mock_kill):
        """When window average drops below 80% of target, sends SIGCONT."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        throttler._samples.extend([10.0, 15.0, 12.0, 8.0, 11.0])
        throttler._is_stopped_state = True
        throttler._sample_cpu = mock.Mock(return_value=10.0)

        throttler._loop_once()

        mock_kill.assert_called_with(9999, signal.SIGCONT)
        self.assertFalse(throttler._is_stopped_state)

    @mock.patch("os.kill")
    def test_throttler_noop_within_target(self, mock_kill):
        """When average is within acceptable range, no signal is sent."""
        from utils.throttle.throttler import ProcessThrottler

        throttler = ProcessThrottler(pid=9999, target_fn=lambda: 50)
        throttler._samples.extend([45.0, 48.0, 42.0, 46.0, 44.0])
        throttler._is_stopped_state = False
        throttler._sample_cpu = mock.Mock(return_value=45.0)

        throttler._loop_once()

        mock_kill.assert_not_called()
        self.assertFalse(throttler._is_stopped_state)
