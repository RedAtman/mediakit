import logging
from unittest import TestCase

logger = logging.getLogger()


class TestCPULimiterCoordinator(TestCase):
    """Tests for CPULimiterCoordinator."""

    def test_coordinator_attach_detach(self):
        """Attaching and detaching PIDs manages throttlers correctly."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._stop_monitor()

        coord.attach(1234)
        self.assertIn(1234, coord._throttlers)

        coord.detach(1234)
        self.assertNotIn(1234, coord._throttlers)

    def test_budget_distribution_even(self):
        """Budget is distributed evenly across active workers."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=False)
        coord._stop_monitor()

        coord.attach(1111)
        coord.attach(2222)
        coord.attach(3333)
        coord.attach(4444)

        budget = coord._calculate_per_process_target()
        self.assertGreaterEqual(budget, 25)

        coord.detach(1111)
        coord.detach(2222)
        coord.detach(3333)
        coord.detach(4444)

    def test_manual_override_priority(self):
        """Manual override takes priority over auto mode."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._stop_monitor()

        coord.set_manual_override(50)
        self.assertTrue(coord._manual_override_active)
        self.assertEqual(coord._manual_target, 50)

        coord.clear_manual_override()
        self.assertFalse(coord._manual_override_active)
        self.assertIsNone(coord._manual_target)

    def test_profile_cycling(self):
        """SIGUSR1 cycles through predefined profiles."""
        from utils.throttle.coordinator import CPULimiterCoordinator

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=True)
        coord._stop_monitor()

        self.assertEqual(coord._profile_index, 0)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 1)
        self.assertEqual(coord._manual_target, 100)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 2)
        self.assertEqual(coord._manual_target, 50)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 3)
        self.assertEqual(coord._manual_target, 25)

        coord._next_profile()
        self.assertEqual(coord._profile_index, 0)
        self.assertIsNone(coord._manual_target)
        self.assertFalse(coord._manual_override_active)

    def test_manual_override_below_min_per_worker(self):
        """Manual override is not floored by MIN_PER_WORKER clamp."""
        from utils.throttle.coordinator import CPULimiterCoordinator, MIN_PER_WORKER

        coord = CPULimiterCoordinator(default_limit=100, auto_mode=False)
        coord._stop_monitor()

        coord.set_manual_override(1)
        budget = coord._calculate_per_process_target()
        self.assertEqual(budget, 1)

        coord.clear_manual_override()
        budget = coord._calculate_per_process_target()
        self.assertGreaterEqual(budget, MIN_PER_WORKER)
