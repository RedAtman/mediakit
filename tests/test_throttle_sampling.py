import os
from unittest import TestCase, main, mock

# /proc/[pid]/stat fields (after comm): S|ppid|pgrp|session|tty|tpgid|flags|...
# indices 0-10 are fields 3-13, indices 11=utime(f14), 12=stime(f15)
# For test: utime=13, stime=14 → (13+14)/100 = 0.27
MOCK_PROC_STAT = (
    '1234 (ffmpeg) S 1 2 3 4 5 6 7 8 9 10 '
    '13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 '
    '30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52'
)


class TestCpuSampling(TestCase):
    """Tests for cross-platform CPU sampling."""

    def test_linux_parse_proc_stat_returns_cpu_time(self):
        """Parsing /proc/[pid]/stat fields 13+14 returns total CPU time in seconds."""
        from utils.throttle.sampling import parse_proc_stat

        cpu_time = parse_proc_stat(MOCK_PROC_STAT)
        self.assertAlmostEqual(cpu_time, 0.27, places=4)

    def test_linux_parse_proc_stat_raises_on_bad_input(self):
        """Malformed stat line raises ValueError."""
        from utils.throttle.sampling import parse_proc_stat

        with self.assertRaises(ValueError):
            parse_proc_stat('garbage')

    def test_linux_sample_cpu_time_reads_proc(self):
        """Sample reads /proc/[pid]/stat and returns float."""
        from utils.throttle.sampling import linux_sample_cpu_time

        with mock.patch('builtins.open', mock.mock_open(read_data=MOCK_PROC_STAT)):
            result = linux_sample_cpu_time(1234)
            self.assertIsInstance(result, float)
            self.assertGreater(result, 0)


class TestMacOSSampling(TestCase):
    """Tests for macOS CPU sampling."""

    def test_parse_ps_time_mmss(self):
        """mm:ss.frac format parses correctly."""
        from utils.throttle.sampling import _parse_ps_time

        self.assertAlmostEqual(_parse_ps_time('01:30.50'), 90.5, places=2)

    def test_parse_ps_time_hhmmss(self):
        """hh:mm:ss format parses correctly."""
        from utils.throttle.sampling import _parse_ps_time

        self.assertAlmostEqual(_parse_ps_time('01:02:30'), 3750.0, places=2)

    def test_parse_ps_time_dd_hhmmss(self):
        """DD-hh:mm:ss format parses correctly."""
        from utils.throttle.sampling import _parse_ps_time

        self.assertAlmostEqual(_parse_ps_time('2-03:30:00'), 185400.0, places=2)

    def test_macos_ps_fallback_parses_output(self):
        """_macos_ps_fallback correctly parses ps output."""
        from utils.throttle.sampling import _macos_ps_fallback

        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '01:30.50 00:15.25\n'
            mock_run.return_value.stderr = ''
            result = _macos_ps_fallback(9999)
            self.assertAlmostEqual(result, 105.75, places=2)

    def test_macos_ps_fallback_raises_on_exit(self):
        """Non-zero ps exit raises ProcessLookupError."""
        from utils.throttle.sampling import _macos_ps_fallback

        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ''
            mock_run.return_value.stderr = 'ps: invalid pid'
            with self.assertRaises(ProcessLookupError):
                _macos_ps_fallback(9999)


class TestSystemLoad(TestCase):
    """Tests for system CPU load monitoring."""

    def test_linux_system_load_parses_proc_stat(self):
        """_linux_system_load parses /proc/stat correctly."""
        from utils.throttle.sampling import _linux_system_load, _LINUX_CPU_LAST

        _LINUX_CPU_LAST['total'] = 0.0
        _LINUX_CPU_LAST['idle'] = 0.0

        mock_stat = 'cpu  1000 200 300 4000 100 50 25 10\n'
        with mock.patch('builtins.open', mock.mock_open(read_data=mock_stat)):
            result1 = _linux_system_load()
            self.assertEqual(result1, 0.0)

        mock_stat2 = 'cpu  2000 400 600 4500 200 100 50 20\n'
        with mock.patch('builtins.open', mock.mock_open(read_data=mock_stat2)):
            result2 = _linux_system_load()
            self.assertGreater(result2, 70.0)
            self.assertLess(result2, 85.0)

    @mock.patch('os.getloadavg', return_value=(2.0, 1.5, 1.0))
    @mock.patch('os.cpu_count', return_value=8)
    def test_macos_system_load_uses_loadavg(self, *_):
        """_macos_system_load calculates usage from loadavg."""
        from utils.throttle.sampling import _macos_system_load

        result = _macos_system_load()
        self.assertAlmostEqual(result, 25.0, places=2)

    @mock.patch('os.getloadavg', return_value=(8.0, 6.0, 4.0))
    @mock.patch('os.cpu_count', return_value=8)
    def test_macos_system_load_high(self, *_):
        """High loadavg produces correct percentage."""
        from utils.throttle.sampling import _macos_system_load

        result = _macos_system_load()
        self.assertAlmostEqual(result, 100.0, places=2)
