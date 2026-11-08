import logging
import unittest

from pydantic import ValidationError

from src import schemas

logger = logging.getLogger()


class SchemaTest(unittest.TestCase):
    def test_accepts_enum_and_number(self):
        state = schemas.State(compress=schemas.StateChoices.finished, trim=2)
        assert isinstance(state, schemas.State)
        assert state.compress == schemas.StateChoices.finished
        assert state.trim == 2

    def test_defaults_to_unprocessed(self):
        state = schemas.State()
        assert state.compress == schemas.StateChoices.unprocessed
        assert state.trim == schemas.StateChoices.unprocessed

    def test_rejects_out_of_range(self):
        # -2 failed / -1 unprocessed / 0.0-1.0 in progress / 2 finished
        for bad in (3, -3):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                schemas.State(compress=bad)
