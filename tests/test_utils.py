import logging
from unittest import TestCase, main

from config import CONFIG
from utils.progress import TqdmProgress
from utils.tools import Dict2Obj

logger = logging.getLogger()


class TestUtils(TestCase):
    def test_dict2obj(self):
        dict2obj = Dict2Obj(CONFIG.CAMERA)
        logger.debug(dict2obj)
        self.assertIsInstance(dict2obj, Dict2Obj)
        logger.debug(dict2obj.__dict__)
        self.assertIsInstance(dict2obj.__dict__, dict)
        # logger.info(dict2obj._dict())
        # self.assertIsInstance(dict2obj._dict(), dict)
        self.assertIsInstance(dict2obj.sony_a7r2, list)
        self.assertIsInstance(dict2obj['sony_a7r2'], list)

    def test_progress_bar_tracks_current_and_percent(self):
        total = 20
        progress = TqdmProgress(total)
        for i in range(total):
            progress.current = i
            self.assertEqual(progress.percent, i / total)
        progress.current = total
        progress.done()
        self.assertEqual(progress.current, total)
        self.assertEqual(progress.percent, 1.0)


if __name__ == '__main__':
    main(verbosity=2)
