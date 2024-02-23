import logging
from typing import Generator, Iterable
import unittest

from sqlalchemy import Integer, func, select, text, update

from config import CONFIG
from folder import Folder
from src import models
from tmp.files import files
from utils import response


logger = logging.getLogger()


class TestFolder(unittest.TestCase):

    # @unittest.mock.patch.object(CONFIG, 'MEDIA_FILE_FOLDER', 'samples')
    def setUp(self) -> None:
        # logger.info(CONFIG.MEDIA_FILE_FOLDER)
        self.folder = Folder(path=CONFIG.MEDIA_FILE_FOLDER)
        return super().setUp()

    def test_class_methods(self):
        result = Folder.get_files(CONFIG.MEDIA_FILE_FOLDER)
        assert isinstance(result, Iterable)
        result = Folder.medias_(CONFIG.MEDIA_FILE_FOLDER)
        assert isinstance(result, Generator)

    def test_methods(self):
        result = self.folder.files
        assert isinstance(result, Iterable)
        result = self.folder.medias
        assert isinstance(result, Generator)

    def test_get_files(self):
        result = self.folder.get_files(CONFIG.MEDIA_FILE_FOLDER)
        logger.debug(result)
        assert isinstance(result, Iterable)

    def test_trim(self):
        result = self.folder.trim(
            files=files,
            callback_list=[
                "compress",
            ],
        )
        assert isinstance(result, dict)

    def test_meta(self):
        result = self.folder.meta
        assert isinstance(result, dict)

    def test_scan_media(self):
        result = self.folder.scan_media()
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result in [200, 400]
        assert result.code in [200, 400]

    def test_scan_media__(self):
        result = Folder.scan_media__(
            Folder.medias_(CONFIG.MEDIA_FILE_FOLDER),
        )
        # logger.debug((len(result), type(result), result))
        # logger.debug((len(result), type(result.code), result, result.code.value))
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result in [200, 400]
        assert result.code in [200, 400]

    def test_query(self):
        folder = Folder(CONFIG.MEDIA_FILE_FOLDER)
        # query = "SELECT media.md5, media.title, media.dirname, media.created_at, media.updated_at, media.state FROM media WHERE media.dirname = :dirname AND state->>'compress' IS NULL"
        query = (
            select(models.Media)
            .where(models.Media.dirname == folder.abspath)
            .where(models.Media.state.op("->>")("compress").cast(Integer) == 2)
        )
        params = {
            "dirname": folder.abspath,
        }
        logger.debug((type(query), query))
        result = folder.query(query, params)
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result == 200
        assert result == "Success"

    def test_query__(self):
        import os

        from utils.db import _sqlalchemy

        query = "SELECT * FROM media"
        query = select(models.Media).where(text("media.dirname = :dirname"))
        logger.info((type(query), query))
        result = Folder.query__(
            _sqlalchemy.Engine(CONFIG.SQLITE_DATABASE),
            query,
            params={
                "dirname": os.path.abspath(CONFIG.MEDIA_FILE_FOLDER),
            },
        )
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result == 200
        assert result == "Success"

    def test_query_update_created_at(self):
        query = (
            update(models.Media)
            .where(models.Media.md5 == "3a51af5d5e4d3c8b84185729e91e0170")
            .values(created_at=func.now())
        )
        result = self.folder.query(query)
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result == 200
        assert result == "Success"

    def test_query_update_state(self):
        query = (
            update(models.Media)
            .where(models.Media.md5 == "3a51af5d5e4d3c8b84185729e91e0170")
            .values(state={"compress": 1})
        )  # can clear another key in state
        query = (
            update(models.Media)
            .where(models.Media.md5 == "3a51af5d5e4d3c8b84185729e91e0170")
            .values(state=func.json_set(models.Media.state, "$.compress", 0))
        )
        result = self.folder.query(query)
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result == 200
        assert result == "Success"

    def test_query__update_state(self):
        query = "UPDATE media SET state = json_set(state, '$.compress', 2) WHERE md5 = '3a51af5d5e4d3c8b84185729e91e0170';"
        from utils.db import _sqlalchemy

        result = Folder.query__(
            _sqlalchemy.Engine(CONFIG.SQLITE_DATABASE),
            query,
        )
        logger.info(result)
        assert isinstance(result, response.Result)
        assert result == 200
        assert result == "Success"

    def test_run(self):
        result = self.folder.run(
            "compress",
            # 'speech_to_text',
            # 'save_text',
            # 'convert_format',
        )
        logger.info(result)
        assert isinstance(result, list)

    def test_run_(self):
        result = Folder.run_(
            "compress",
            # 'speech_to_text',
            # 'save_text',
            # 'convert_format',
        )
        logger.info(result)
        assert isinstance(result, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
