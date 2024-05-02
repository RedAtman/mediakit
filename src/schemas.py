from enum import IntEnum
import logging

from pydantic import BaseModel, Field, ValidationError, ValidationInfo, field_validator


logger = logging.getLogger()

__all__ = [
    "StateChoices",
    "State",
]


class StateChoices(IntEnum):
    failed = -2
    unprocessed= -1
    finished = 2

    @classmethod
    def __str__(cls) -> str:
        return str({key: value._value_ for key, value in cls._member_map_.items()})


_state_field = Field(
    ge=StateChoices.failed,
    le=StateChoices.finished,
    default=StateChoices.unprocessed,
    # description="-2 is failed, -1 is unprocessed, 0.0 - 1.0 is in progress, 2 is finished.",
    description=StateChoices.__str__(),
    validate_default=True,
)


class State(BaseModel):
    compress: float = _state_field
    trim: float = _state_field
    # compress: StateChoices = StateChoices.unprocessed
    # trim: StateChoices = StateChoices.unprocessed

    class Config:
        from_attributes = True

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}({self.__dict__})>"

    def __getitem__(self, key):
        return self.__dict__.get(key)

    @field_validator("compress", "trim")
    @classmethod
    def field_validator(cls, value: float, info: ValidationInfo) -> float:
        assert (
            StateChoices.failed <= value <= StateChoices.finished
        ), f"{info.field_name} must be between 0 and 1."
        return value


if __name__ == "__main__":
    from config import CONFIG

    logger.info(StateChoices.__str__())

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
