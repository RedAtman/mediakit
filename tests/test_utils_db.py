import logging
import unittest

from config import CONFIG
from utils.db import _sqlalchemy


logger = logging.getLogger()


class EngineTest(unittest.TestCase):
    def setUp(self):
        # self.engine = _sqlmodel.Engine(CONFIG.SQLITE_DATABASE)
        self.engine = _sqlalchemy.Engine(CONFIG.SQLITE_DATABASE)

    def test_create_db_tables(self):

        result = self.engine.create_db_and_tables()
        logger.info(result)
        assert result is None
