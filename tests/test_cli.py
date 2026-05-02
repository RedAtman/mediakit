import logging
import tempfile
from unittest import TestCase, mock



logger = logging.getLogger()


class TestParser(TestCase):
    def setUp(self):
        from utils.cli import create_parser

        self.parser = create_parser()
        self.kwargs = self.parser.parse_args(
            [
                "compress",
                "--type",
                "video",
                "--max_workers",
                "2",
                "--daemon",
                "True",
            ]
        )
        logger.info(self.kwargs)
        logger.info(self.kwargs.__dict__)

    def test_parse_kwargs(self):
        assert self.kwargs.action == "compress"
        assert self.kwargs.type == "video"
        assert isinstance(self.kwargs.max_workers, int)
        assert self.kwargs.daemon is True

    @mock.patch("folder.Folder.scan_media")
    def test_cli(self, mock_scan_media):
        from folder import Folder

        mock_scan_media.return_value = []
        temp_dir = tempfile.mkdtemp()
        folder = Folder(temp_dir)
        result = folder.scan_media()
        logger.info(result)
        assert isinstance(result, list)


class TestWatchCliArgs(TestCase):
    def setUp(self):
        from utils.cli import create_parser
        self.parser = create_parser()

    def test_watch_action_parses(self):
        kwargs = self.parser.parse_args(['watch', '-f', '/tmp/media'])
        self.assertEqual(kwargs.action, 'watch')

    def test_watch_default_folder(self):
        kwargs = self.parser.parse_args(['watch'])
        self.assertEqual(kwargs.action, 'watch')

    def test_watch_no_recursive_flag(self):
        kwargs = self.parser.parse_args(['watch', '--no-recursive'])
        self.assertTrue(kwargs.no_recursive)

    def test_watch_recursive_default_is_false(self):
        kwargs = self.parser.parse_args(['watch'])
        self.assertFalse(kwargs.no_recursive)

    def test_watch_no_scan_existing_flag(self):
        kwargs = self.parser.parse_args(['watch', '--no-scan-existing'])
        self.assertTrue(kwargs.no_scan_existing)

    def test_watch_scan_existing_default_is_false(self):
        kwargs = self.parser.parse_args(['watch'])
        self.assertFalse(kwargs.no_scan_existing)

    def test_watch_reuses_standard_flags(self):
        kwargs = self.parser.parse_args(['watch', '-t', 'video', '-w', '4', '-c', '50'])
        self.assertEqual(kwargs.action, 'watch')
        self.assertEqual(kwargs.type, 'video')
        self.assertEqual(kwargs.max_workers, 4)
        self.assertEqual(kwargs.cpu_limit, 50)


if __name__ == "__main__":
    import unittest
    unittest.main()
