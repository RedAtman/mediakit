import logging
import tempfile
import unittest
from unittest import mock

from config import CONFIG
from folder import Folder
from src.schedulers import folder as scheduler_folder


logger = logging.getLogger()


class TestScheduler(unittest.TestCase):

    def setUp(self):
        from utils.cli import create_parser

        self.parser = create_parser()
        self.temp_dir = tempfile.mkdtemp()
        self.kwargs = self.parser.parse_args(
            [
                "compress",
                "--type",
                "video",
                "--max_workers",
                "2",
                "--daemon",
                "True",
                "--folder",
                self.temp_dir,
            ]
        )
        logger.info(self.kwargs)
        logger.info(self.kwargs.__dict__)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @mock.patch("src.schedulers.folder._compress")
    @mock.patch("src.schedulers.folder._query")
    @mock.patch("src.schedulers.folder._scan")
    def test_cli(self, mock_scan, mock_query, mock_compress):
        mock_scan.return_value = None
        mock_query.return_value = []
        mock_compress.return_value = []
        scheduler = getattr(scheduler_folder, self.kwargs.action)
        result = getattr(scheduler, "core")(**self.kwargs.__dict__)
        logger.info(result)
        assert result is None or isinstance(result, list)

    def test_query(self):
        ctx = scheduler_folder.Context()
        kwargs = self.kwargs.__dict__.copy()
        folder = Folder(self.temp_dir)
        kwargs["folder"] = folder
        result = scheduler_folder._query(ctx=ctx, **kwargs)
        logger.info(result)


if __name__ == "__main__":
    unittest.main()
