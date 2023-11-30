from typing import Generator, Iterable
from unittest import TestCase, main, mock

from config import CONFIG
from folder import Folder
from logger import logger
from tmp.files import files


class TestFolder(TestCase):

    @mock.patch.object(CONFIG, 'MEDIA_FILE_FOLDER', '/Users/nut/Downloads/rs/202311/_/264')
    # @mock.patch.object(CONFIG, 'MEDIA_FILE_FOLDER', '/Volumes/ssd2t/_rs/木下/uncompress')
    def setUp(self) -> None:
        # logger.info(CONFIG.MEDIA_FILE_FOLDER)
        self.folder = Folder(path=CONFIG.MEDIA_FILE_FOLDER)
        return super().setUp()

    def test_class_methods(self):
        result = Folder.get_files(CONFIG.MEDIA_FILE_FOLDER)
        self.assertIsInstance(result, Iterable)
        result = Folder.get_medias(CONFIG.MEDIA_FILE_FOLDER)
        self.assertIsInstance(result, Generator)

    def test_methods(self):
        result = self.folder.files
        self.assertIsInstance(result, Iterable)
        result = self.folder.medias
        self.assertIsInstance(result, Generator)

    def test_trim(self):
        result = self.folder.trim(
            files=files,
            callback_list=[
                'compress',
            ]
        )
        self.assertIsInstance(result, dict)

    def test_compress(self):
        result = self.folder.compress()
        logger.info(result)
        self.assertEqual(result, None)


if __name__ == '__main__':
    testcase = TestFolder()
    testcase.setUp()
    testcase.test_compress()
    main(verbosity=2)
