import logging
import tempfile
from typing import Generator, Iterable
import unittest
from unittest import mock

from sqlalchemy import Integer, func, select, text, update

from config import CONFIG
from folder import Folder
from src import models
from tmp.files import files
from utils import response


logger = logging.getLogger()


class TestFolder(unittest.TestCase):

    def setUp(self) -> None:
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.folder = Folder(path=self.temp_dir)
        return super().setUp()

    def tearDown(self) -> None:
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        return super().tearDown()

    def test_class_methods(self):
        result = Folder.get_files(self.temp_dir)
        assert isinstance(result, Iterable)
        result = Folder.medias_(self.temp_dir)
        assert isinstance(result, Generator)

    def test_methods(self):
        result = self.folder.files
        assert isinstance(result, Iterable)
        result = self.folder.medias
        assert isinstance(result, Generator)

    def test_get_files(self):
        result = self.folder.get_files(self.temp_dir)
        logger.debug(result)
        assert isinstance(result, Iterable)

    @unittest.skip("Requires specific files to exist")
    @mock.patch.object(CONFIG, "MEDIA_FILE_FOLDER", "samples")
    def test_trim(self):
        result = self.folder.trim(
            files=files,
            callback_list=[
                "compress",
            ],
        )
        assert isinstance(result, dict)

    def test_scan_media(self):
        result = self.folder.scan_media()
        logger.info(result)
        assert isinstance(result, list)

    def test_scan_media__(self):
        result = Folder.scan_media__(
            Folder.medias_(self.temp_dir),
        )
        logger.info(result)
        assert isinstance(result, list)

    def test_query(self):
        folder = Folder(self.temp_dir)
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
        assert result.code == response.ResultStatus.SUCCESS

    @unittest.skip("Folder.query__ is not implemented")
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
                "dirname": os.path.abspath(self.temp_dir),
            },
        )
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result.code == response.ResultStatus.SUCCESS

    def test_query_update_created_at(self):
        # First create a test media record
        models.Media.get_or_create(
            md5="3a51af5d5e4d3c8b84185729e91e0170",
            title="test.mp4",
            dirname=self.temp_dir,
        )
        query = (
            update(models.Media)
            .where(models.Media.md5 == "3a51af5d5e4d3c8b84185729e91e0170")
            .values(created_at=func.now())
        )
        result = self.folder.query(query)
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result.code == response.ResultStatus.SUCCESS

    def test_query_update_state(self):
        # First create a test media record
        models.Media.get_or_create(
            md5="3a51af5d5e4d3c8b84185729e91e0170",
            title="test.mp4",
            dirname=self.temp_dir,
        )
        query = (
            update(models.Media)
            .where(models.Media.md5 == "3a51af5d5e4d3c8b84185729e91e0170")
            .values(state={"compress": 1})
        )
        query = (
            update(models.Media)
            .where(models.Media.md5 == "3a51af5d5e4d3c8b84185729e91e0170")
            .values(state=func.json_set(models.Media.state, "$.compress", 0))
        )
        result = self.folder.query(query)
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result.code == response.ResultStatus.SUCCESS

    @unittest.skip("Folder.query__ is not implemented")
    def test_query__update_state(self):
        query = "UPDATE media SET state = json_set(state, '$.compress', 2) WHERE md5 = '3a51af5d5e4d3c8b84185729e91e0170';"
        from utils.db import _sqlalchemy

        result = Folder.query__(
            _sqlalchemy.Engine(CONFIG.SQLITE_DATABASE),
            query,
        )
        logger.info(result)
        assert isinstance(result, response.Result)
        assert result.code == response.ResultStatus.SUCCESS

    @mock.patch("folder.Folder.scan_media")
    def test_run(self, mock_scan_media):
        mock_scan_media.return_value = response.Result(code=response.ResultStatus.SUCCESS, data={})
        result = self.folder.run(
            "compress",
        )
        logger.info(result)
        assert isinstance(result, list)

    @mock.patch("folder.Folder.scan_media")
    def test_run_(self, mock_scan_media):
        mock_scan_media.return_value = response.Result(code=response.ResultStatus.SUCCESS, data={})
        result = Folder.run_(
            "compress",
            path=self.temp_dir,
        )
        logger.info(result)
        assert isinstance(result, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
