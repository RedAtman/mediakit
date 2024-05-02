import logging
import unittest

from folder import Folder
from src.schedulers import folder as scheduler_folder


logger = logging.getLogger()


class TestScheduler(unittest.TestCase):

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
                # '--flag', 'True',
            ]
        )
        logger.info(self.kwargs)
        logger.info(self.kwargs.__dict__)
        # logger.info(type(self.kwargs.daemon))
        # logger.info((type(self.kwargs.flag), self.kwargs.flag))

    def test_cli(self):
        scheduler = getattr(scheduler_folder, self.kwargs.action)
        # logger.debug(scheduler)
        result = getattr(scheduler, "core")(**self.kwargs.__dict__)
        logger.info(result)
        assert isinstance(result, list)

    def test_query(self):
        ctx = scheduler_folder.Context()
        kwargs = self.kwargs.__dict__
        folder = Folder(self.kwargs.folder)
        kwargs["folder"] = folder
        result = scheduler_folder._query(ctx=ctx, **kwargs)
        logger.info(result)


if __name__ == "__main__":
    unittest.main()
