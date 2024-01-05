import unittest

from logger import logger
from src import models


class DbEngineTest(unittest.TestCase):
    def setUp(self):
        self.media = models.Media.get_or_create(md5='3a51af5d5e4d3c8b84185729e91e0170')

    def test_update_state(self):
        result = self.media.update_state('compress', 1)
        logger.json(result)
        assert isinstance(result, models.Media)
