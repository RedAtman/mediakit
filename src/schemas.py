from enum import IntEnum
import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

logger = logging.getLogger()

__all__ = ['StateChoices', 'State']


class StateChoices(IntEnum):
    failed = -2
    unprocessed = -1
    finished = 2
    # ffprobe 根本打不开 (AppleDouble `._foo.mp4` 这类扩展名骗人的文件):
    # 既不是失败也不该重试, 所以单独给一个终态
    ignored = -3

    @classmethod
    def __str__(cls) -> str:
        return str({key: value._value_ for key, value in cls._member_map_.items()})


# 没有默认值: "这个 action 没被执行过" 就不该在 state 里留下 key (见 State.dump).
_state_field = Field(
    default=None,
    ge=StateChoices.ignored,
    le=StateChoices.finished,
    # description="-3 ignored, -2 is failed, -1 is unprocessed, 0.0 - 1.0 is in progress, 2 is finished.",
    description=StateChoices.__str__(),
)


class State(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    compress: float | None = _state_field
    trim: float | None = _state_field

    def dump(self) -> dict[str, float]:
        """只保留真正写过状态的 action.

        未执行过的 action 不落库: 以前新建一行就带 `{"compress": -1, "trim": -1}`,
        而 trim 从来没有 scheduler 写它, 那些 key 是纯噪音. 缺失的 key 语义等于
        unprocessed(-1), QUERY_UNPROCESSED 用 coalesce 兜住.
        """
        return self.model_dump(exclude_none=True)

    def __str__(self) -> str:
        return f'<{self.__class__.__name__}({self.__dict__})>'

    def __getitem__(self, key):
        return self.__dict__.get(key)

    @field_validator('compress', 'trim')
    @classmethod
    def field_validator(cls, value: float | None, info: ValidationInfo) -> float | None:
        if value is None:
            return None
        assert StateChoices.ignored <= value <= StateChoices.finished, (
            f'{info.field_name} must be between {StateChoices.ignored} and {StateChoices.finished}.'
        )
        return value


if __name__ == '__main__':
    logger.info(StateChoices.__str__())

    state = State()
    logger.info((type(state), state))
    logger.info(state.model_dump())
    setattr(state, 'trim', 'value')
    logger.info((type(state), state))
    logger.info(state.model_dump())
    _dict = {'key': 'value'}
    logger.info(
        (
            'dict',
            type(_dict),
            _dict,
            _dict.keys(),
            'key' in _dict,
            _dict['key'],
            hasattr(dict, 'key'),
            getattr(_dict, 'key', '233'),
        )
    )

    logger.info(State.model_fields.keys())
    logger.info('compress' in State.model_fields.keys())

    try:
        # result = State()
        # result = State(compress=2, trim=3)
        result = State(compress=3)
        logger.info(result)
    except ValidationError as err:
        logger.exception(err)
