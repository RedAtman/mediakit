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



class TestWatchFlag(TestCase):
    def test_watch_flag_on_compress(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['compress', '--watch'])
        self.assertTrue(kwargs.watch)
        self.assertEqual(kwargs.action, 'compress')

    def test_watch_default_is_false(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['compress'])
        self.assertFalse(kwargs.watch)

    def test_watch_reuses_standard_flags(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['compress', '--watch', '-t', 'video', '-w', '4', '-c', '50'])
        self.assertTrue(kwargs.watch)
        self.assertEqual(kwargs.action, 'compress')
        self.assertEqual(kwargs.type, 'video')
        self.assertEqual(kwargs.max_workers, 4)
        self.assertEqual(kwargs.cpu_limit, 50)

    def test_watch_recursive_flag(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['compress', '--watch', '--recursive'])
        self.assertTrue(kwargs.recursive)

    def test_watch_no_scan_existing_flag(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['compress', '--watch', '--no-scan-existing'])
        self.assertTrue(kwargs.no_scan_existing)

    def test_watch_works_with_different_actions(self):
        from utils.cli import create_parser
        kwargs = create_parser().parse_args(['trim', '--watch'])
        self.assertTrue(kwargs.watch)
        self.assertEqual(kwargs.action, 'trim')

    def test_watch_folder_file_on_compress(self):
        from utils.cli import create_parser
        result = create_parser().parse_args(['compress', '--watch', '--folder-file', '/my/paths.txt'])
        self.assertEqual(result.folder_file, '/my/paths.txt')

    def test_watch_folder_file_defaults_to_none(self):
        from utils.cli import create_parser
        result = create_parser().parse_args(['compress', '--watch'])
        self.assertIsNone(result.folder_file)


if __name__ == "__main__":
    import unittest
    unittest.main()
