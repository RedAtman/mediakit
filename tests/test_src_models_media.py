import logging
import unittest
import uuid

from src.models import Media
from src.schemas import StateChoices
from utils import response


logger = logging.getLogger()


class MediaTest(unittest.TestCase):
    def setUp(self):
        # Use a unique md5 for each test to avoid UNIQUE constraint violations
        self.test_md5 = str(uuid.uuid4())
        self.model: Media = Media.get_or_create(
            md5=self.test_md5,
            title="test_video",
            dirname="/tmp/test",
        )

    def tearDown(self):
        # Clean up the test record
        try:
            self.model.delete()
        except Exception:
            pass

    def test_update_state(self):
        result = self.model.update_state("compress", StateChoices.finished)
        logger.debug(result)
        assert isinstance(result, response.Result)
