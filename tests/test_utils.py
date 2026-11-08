import logging
from unittest import TestCase, main

from utils.progress import TqdmProgress
from utils.tools import Dict2Obj

logger = logging.getLogger()


class TestUtils(TestCase):
    def test_dict2obj(self):
        # CONFIG.CAMERA comes from the CAMERA env var ({} when absent, as on CI),
        # so assert against a fixed payload instead of whatever .env happens to hold
        camera = {'sony_a7r2': ['laowa_12mm_f2.8']}
        dict2obj = Dict2Obj(camera)
        self.assertIsInstance(dict2obj, Dict2Obj)
        self.assertIsInstance(dict2obj.__dict__, dict)
        # Dict2Obj 是动态属性访问, getattr 走的就是 __getattr__
        self.assertEqual(getattr(dict2obj, 'sony_a7r2'), ['laowa_12mm_f2.8'])
        self.assertEqual(dict2obj['sony_a7r2'], ['laowa_12mm_f2.8'])

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
