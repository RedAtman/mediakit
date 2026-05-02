import logging
import unittest

from src.models.media import Media


logger = logging.getLogger()


class TestModel(unittest.TestCase):
    def setUp(self):
        self.model = Media.get_or_create(
            md5="1234567890",
            title="zh.mp4",
            dirname="samples",
        )
        logger.info(self.model)
