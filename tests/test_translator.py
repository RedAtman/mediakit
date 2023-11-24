import unittest

from utils import Translator


class TestTranslator(unittest.TestCase):

    def test_translate(self):
        text = ["白云", "蓝天", "天空"]
        text = ['白云', '蓝天', '天空', '山顶', '自驾游', '驾车', '冰山梁']
        result = Translator.translate(text)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), len(text))


if __name__ == '__main__':
    # testcase = TestTranslator()
    # testcase.test_translate()
    unittest.main(verbosity=2)
