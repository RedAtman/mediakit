import unittest

from logger import logger
from src import schemas


class SchemaTest(unittest.TestCase):

    def test_validate(self):
        _state = {
            'compress': schemas.StateChoices.running,
            'trim': 2,
        }
        state = schemas.State(**_state)
        logger.json(state)
        assert isinstance(state, schemas.State)
        assert state.compress == _state['compress']

        _state = {
            'compress': schemas.StateChoices.running,
            'trim': 20,
        }
        from pydantic import ValidationError
        try:
            state = schemas.State(**_state)
        except ValidationError as err:
            logger.error(err)
            assert isinstance(err, ValidationError)
