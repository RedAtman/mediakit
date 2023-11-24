import unittest


class UserCase(unittest.TestCase):

    def test_haha(self):
        print('我是一个测试')
        self.assertEqual(1, 1)

    def a(self):  # 这一个函数是不会执行的
        print('我不是一个测试')


if __name__ == '__main__':
    unittest.main()
