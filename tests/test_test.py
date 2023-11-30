from unittest import TestCase, main, mock

from config import CONFIG
from logger import logger


class T0:
    tag = 'unpatched'


class T1(T0):
    pass


class TestMock(TestCase):

    def test_hello(self):
        logger.info('I am test_hello.')
        self.assertEqual(1, 1)

    # @mock.patch.object(T1, 'tag', mock.MagicMock(return_value='patched'))
    @mock.patch.object(T1, 'tag', 'patched')
    def test_tag(self):
        logger.info(T1.tag)
        self.assertEqual('patched', T1.tag)
        self.assertEqual('patched', T1().tag)

    # @mock.patch.dict(os.environ, {'MEDIA_FILE_FOLDER': 'patched'})
    # @mock.patch('config.CONFIG', 'MEDIA_FILE_FOLDER', 'patched')
    @mock.patch.object(CONFIG, 'MEDIA_FILE_FOLDER', 'patched')
    def test_mock(self):
        logger.info(CONFIG)
        logger.debug(CONFIG.MEDIA_FILE_FOLDER)
        logger.info(CONFIG())
        logger.info(CONFIG.__dict__)
        self.assertEqual(CONFIG.MEDIA_FILE_FOLDER, 'patched')
        self.assertEqual(CONFIG().MEDIA_FILE_FOLDER, 'patched')

    @mock.patch("config.BASE_DIR", 'patched')
    def test_mock02(self):
        from config import BASE_DIR  # pylint: disable=import-outside-toplevel
        logger.debug(BASE_DIR)
        self.assertEqual(BASE_DIR, 'patched')


if __name__ == '__main__':
    main()
