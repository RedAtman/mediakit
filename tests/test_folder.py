from typing import Generator, Iterable
from unittest import TestCase, main, mock

from config import CONFIG
from folder import Folder
from logger import logger
from tmp.files import files


class TestFolder(TestCase):

    @mock.patch.object(CONFIG, 'MEDIA_FILE_FOLDER', 'samples')
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

    def test_get_files(self):
        result = self.folder.get_files(CONFIG.MEDIA_FILE_FOLDER)
        logger.debug(result)
        self.assertIsInstance(result, Iterable)

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

    def test_meta(self):
        result = self.folder.meta
        self.assertIsInstance(result, dict)

    def test_get_texts(self):
        result = self.folder.get_texts()
        self.assertIsInstance(result, Generator)

    def test_save_texts(self):
        result = self.folder.save_texts()
        self.assertEqual(result, dict)

    def test_convert_format(self):
        result = self.folder.convert_format()
        self.assertEqual(result, dict)

if __name__ == '__main__':
    main(verbosity=2)
