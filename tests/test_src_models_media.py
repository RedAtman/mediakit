import logging
import unittest

from src.models import Media
from src.schemas import StateChoices


logger = logging.getLogger()


class MediaTest(unittest.TestCase):
    def setUp(self):
        self.model: Media = Media.get_or_create(md5="3a51af5d5e4d3c8b84185729e91e0170")

    def test_update_state(self):
        result = self.model.update_state("compress", StateChoices.finished)
        logger.debug(result)
        assert isinstance(result, Media)
