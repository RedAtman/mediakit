import logging
import tempfile
from typing import Generator, Iterable
import unittest
from unittest import mock
import uuid

from sqlalchemy import Integer, func, select, update

from folder import Folder
from src import models
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

    def test_scan_media(self):
        result = self.folder.scan_media()
        logger.info(result)
        assert hasattr(result, '__iter__')

    def test_scan_media__(self):
        result = Folder.scan_media__(Folder.medias_(self.temp_dir))
        logger.info(result)
        assert hasattr(result, '__iter__')

    def test_query(self):
        folder = Folder(self.temp_dir)
        query = (
            select(models.Media)
            .where(models.Media.dirname == folder.abspath)
            .where(models.Media.state.op('->>')('compress').cast(Integer) == 2)
        )
        params = {'dirname': folder.abspath}
        logger.debug((type(query), query))
        result = folder.query(query, params)
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result.code == response.ResultStatus.SUCCESS

    def test_query_unprocessed_includes_failed(self):
        """QUERY_UNPROCESSED must return both unprocessed (-1) and failed (-2) files,
        so a transient failure (e.g. bad ffmpeg path at startup) does not strand files."""
        import uuid

        from src.schemas import StateChoices

        folder = Folder(self.temp_dir)
        # Insert two records in the temp dir: one failed, one unprocessed.
        failed_md5 = str(uuid.uuid4())
        unprocessed_md5 = str(uuid.uuid4())
        failed_model = models.Media.get_or_create(md5=failed_md5, title='failed.mp4', dirname=folder.abspath)
        unprocessed_model = models.Media.get_or_create(
            md5=unprocessed_md5, title='unprocessed.mp4', dirname=folder.abspath
        )
        try:
            failed_model.update_state('compress', StateChoices.failed)
            unprocessed_model.update_state('compress', StateChoices.unprocessed)
            query = folder.get_query_statement('QUERY_UNPROCESSED')
            self.assertIsNotNone(query)
            result = folder.query(query)
            self.assertIsInstance(result, response.Result)
            self.assertEqual(result.code, response.ResultStatus.SUCCESS)
            paths = {m.title for m in result.data}
            self.assertIn('failed.mp4', paths)
            self.assertIn('unprocessed.mp4', paths)
        finally:
            failed_model.delete()
            unprocessed_model.delete()

    def test_query_update_created_at(self):
        md5 = str(uuid.uuid4())
        models.Media.get_or_create(md5=md5, title='test.mp4', dirname=self.temp_dir)
        query = update(models.Media).where(models.Media.md5 == md5).values(created_at=func.now())
        result = self.folder.query(query)
        logger.info(result)
        assert isinstance(result, dict)
        assert isinstance(result, response.Result)
        assert result.code == response.ResultStatus.SUCCESS

    def test_query_update_state(self):
        md5 = str(uuid.uuid4())
        model = models.Media.get_or_create(md5=md5, title='test.mp4', dirname=self.temp_dir)
        try:
            query = (
                update(models.Media)
                .where(models.Media.md5 == md5)
                .values(state=func.json_set(models.Media.state, '$.compress', 0))
            )
            result = self.folder.query(query)
            logger.info(result)
            assert isinstance(result, dict)
            assert isinstance(result, response.Result)
            assert result.code == response.ResultStatus.SUCCESS
            # data 只回报命中行数, 不再泄露 CursorResult 内部结构
            assert result.data == {'rowcount': 1}
        finally:
            model.delete()

    def test_query_update_matching_nothing_reports_failed(self):
        query = update(models.Media).where(models.Media.md5 == 'no-such-md5').values(title='x')
        result = self.folder.query(query)
        self.assertIsInstance(result, response.Result)
        self.assertEqual(result.code, response.ResultStatus.FAILED)

    @mock.patch('folder.Folder.scan_media')
    def test_run(self, mock_scan_media):
        mock_scan_media.return_value = response.Result(code=response.ResultStatus.SUCCESS, data={})
        result = self.folder.run('compress')
        logger.info(result)
        assert isinstance(result, list)

    @mock.patch('folder.Folder.scan_media')
    def test_run_(self, mock_scan_media):
        mock_scan_media.return_value = response.Result(code=response.ResultStatus.SUCCESS, data={})
        result = Folder.run_('compress', path=self.temp_dir)
        logger.info(result)
        assert isinstance(result, list)


if __name__ == '__main__':
    unittest.main(verbosity=2)
