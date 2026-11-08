import logging
import tempfile
from unittest import TestCase, mock

logger = logging.getLogger()


class TestParser(TestCase):
    def setUp(self):
        from utils.cli import create_parser

        self.parser = create_parser()
        self.kwargs = self.parser.parse_args(['compress', '--type', 'video', '--max_workers', '2', '--daemon', 'True'])
        logger.info(self.kwargs)
        logger.info(self.kwargs.__dict__)

    def test_parse_kwargs(self):
        assert self.kwargs.action == 'compress'
        assert self.kwargs.type == 'video'
        assert isinstance(self.kwargs.max_workers, int)
        assert self.kwargs.daemon is True

    @mock.patch('folder.Folder.scan_media')
    def test_cli(self, mock_scan_media):
        from folder import Folder

        mock_scan_media.return_value = []
        temp_dir = tempfile.mkdtemp()
        folder = Folder(temp_dir)
        result = folder.scan_media()
        logger.info(result)
        assert hasattr(result, '__iter__')


class TestCompressOutputFlags(TestCase):
    def test_resolution_and_fps(self):
        from utils.cli import create_parser
        from utils.video import VideoResolution

        kwargs = create_parser().parse_args(['compress', '--resolution', 'FHD', '--fps', '30'])
        # argparse type 已把字符串解析成枚举, 非法值在解析阶段就会退出
        self.assertIs(kwargs.resolution, VideoResolution.FHD)
        self.assertEqual(kwargs.fps, 30)

    def test_default_none_falls_back_to_config(self):
        from utils.cli import create_parser

        kwargs = create_parser().parse_args(['compress'])
        # None 表示交给 CONFIG.COMPRESS_RESOLUTION / CONFIG.COMPRESS_FPS 兜底
        self.assertIsNone(kwargs.resolution)
        self.assertIsNone(kwargs.fps)

    def test_invalid_resolution_exits_at_parse_time(self):
        from utils.cli import create_parser

        with self.assertRaises(SystemExit):
            create_parser().parse_args(['compress', '--resolution', '1080p'])

    def test_invalid_fps_exits_at_parse_time(self):
        from utils.cli import create_parser

        with self.assertRaises(SystemExit):
            create_parser().parse_args(['compress', '--fps', '0'])


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


if __name__ == '__main__':
    import unittest

    unittest.main()
