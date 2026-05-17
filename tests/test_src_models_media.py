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

    def test_get_or_create_updates_title_dirname_on_existing_md5(self):
        m1 = Media.get_or_create(
            md5=self.test_md5,
            title="original.mp4",
            dirname="/tmp/original",
        )
        self.assertEqual(m1.title, "original.mp4")
        self.assertEqual(m1.dirname, "/tmp/original")

        m2 = Media.get_or_create(
            md5=self.test_md5,
            title="moved.mp4",
            dirname="/tmp/moved",
        )
        self.assertEqual(m2.title, "moved.mp4")
        self.assertEqual(m2.dirname, "/tmp/moved")
        self.assertIsNotNone(m2.updated_at)
        self.assertEqual(m2.state, {"compress": -1, "trim": -1})
        self.model = m2

    def test_update_state(self):
        result = self.model.update_state("compress", StateChoices.finished)
        logger.debug(result)
        assert isinstance(result, response.Result)
