import logging
import unittest


logger = logging.getLogger()


class ParserTest(unittest.TestCase):
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

    def test_parse_kwargs(self):
        assert self.kwargs.action == "compress"
        assert self.kwargs.type == "video"
        assert isinstance(self.kwargs.max_workers, int)
        assert self.kwargs.daemon is True
        # assert args.flag is False

    def test_cli(self):
        from folder import Folder

        folder = Folder(self.kwargs.folder)
        result = folder.scan_media()
        logger.info(result)
        assert isinstance(result, list)
