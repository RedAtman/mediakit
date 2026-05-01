import logging
import tempfile
from unittest import TestCase, mock

from config import CONFIG


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


if __name__ == "__main__":
    import unittest
    unittest.main()
