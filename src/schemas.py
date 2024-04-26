from enum import IntEnum
import logging

from pydantic import BaseModel, ValidationError


logger = logging.getLogger()


class StateChoices(IntEnum):
    undo = 0
    running = 1
    finished = 2


class State(BaseModel):
    compress: StateChoices = StateChoices.undo
    trim: StateChoices = StateChoices.undo
    # compress: StateChoices = Field(StateChoices.undo, description="Error messages if any")
    # trim: StateChoices = Field(StateChoices.undo, description="Error messages if any")

    class Config:
        from_attributes = True

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}({self.__dict__})>"

    def __getitem__(self, key):
        return self.__dict__.get(key)

    # @validator('compress')


if __name__ == "__main__":
    from config import CONFIG

    state = State()
    logger.info((type(state), state))
    logger.info(state.model_dump())
    setattr(state, "trim", "value")
    logger.info((type(state), state))
    logger.info(state.model_dump())
    _dict = {
        "key": "value",
    }
    logger.info(
        (
            "dict",
            type(_dict),
            _dict,
            _dict.keys(),
            "key" in _dict,
            _dict["key"],
            hasattr(dict, "key"),
            getattr(_dict, "key", "233"),
        )
    )

    logger.info(State.model_fields.keys())
    logger.info("compress" in State.model_fields.keys())

    try:
        # result = State()
        # result = State(compress=2, trim=3)
        result = State(compress=3)
        logger.info(result)
    except ValidationError as err:
        logger.exception(err)
