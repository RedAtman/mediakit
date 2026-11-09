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


class TestMediaCategories(TestCase):
    """媒体类型清单必须只有一份真相 (utils/media.py), 其余模块引用它."""

    def test_every_processable_category_exists_in_the_registry(self):
        import json
        import pathlib

        from utils.media import MEDIA_CATEGORIES

        registry = json.loads((pathlib.Path('utils') / 'media_types.json').read_text())
        for category in MEDIA_CATEGORIES:
            self.assertIn(category, registry, f'{category} 没有扩展名映射, guess() 永远猜不出来')

    def test_base_and_dedupe_share_the_single_list(self):
        from base.media import BaseMedia
        from src.schedulers.dedupe import MEDIA_CATEGORIES

        self.assertEqual(set(BaseMedia._INCLUDE_TYPE), set(MEDIA_CATEGORIES))
