import logging
import time
from unittest import main, TestCase

from config import CONFIG
from utils.tools import Dict2Obj, loading_bar, progressbar


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
        logger.debug(dict2obj.sony_a7r2)
        self.assertIsInstance(dict2obj.sony_a7r2, list)
        logger.info(dict2obj["sony_a7r2"])
        logger.info(dict2obj["sony_a7r2"][0])
        self.assertIsInstance(dict2obj["sony_a7r2"], list)

    def test_progress_bar(self):
        total = 20
        progress = ProgressBar(total)
        for i in range(0, total):
            progress.current = i
            time.sleep(0.1)
        progress.done()

    def test_loading_bar(self):
        total = 20
        for i in range(0, total):
            loading_bar(i, total, 2)
            time.sleep(0.1)

    def test_progressbar(self):
        total = 20
        for _ in progressbar(total):
            time.sleep(0.1)


if __name__ == "__main__":
    main(verbosity=2)
