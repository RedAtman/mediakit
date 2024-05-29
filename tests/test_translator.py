import logging
from unittest import TestCase, main

from utils.translator import Translator


logger = logging.getLogger()


class TestTranslator(TestCase):

    def test_translate(self):
        text = ["白云", "蓝天", "天空"]
        text = ["白云", "蓝天", "天空", "山顶", "自驾游", "驾车", "冰山梁"]
        result = Translator.translate(text)
        logger.info(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), len(text))


if __name__ == "__main__":
    main(verbosity=2)
