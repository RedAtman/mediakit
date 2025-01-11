from enum import IntEnum
from http import HTTPStatus
from itertools import chain
from typing import Any, Dict, Optional, Union


class _StatusConstructor(IntEnum):
    """Status constructor.

    e.g.
        args = "CONTINUE", ("100", "Continue", "Request received")
        obj = _StatusConstructor(*args)
    """

    value: int
    _value_: int
    phrase: str
    description: str

    def __new__(cls, value: int, phrase: str = "", description: str = ""):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.phrase = phrase
        obj.description = description
        return obj

    def __eq__(self, __value: object) -> bool:
        if __value == self.phrase:
            return True
        return super().__eq__(__value)


class ResultStatus(_StatusConstructor):
    SUCCESS = 0, "Success", "Success"
    FAILED = 1, "Failed", "Failed"
    DATABASE_ERROR = 600, "Database Error", "Database Error"
    KEYBOARD_INTERRUPT = 601, "Keyboard Interrupt", "Keyboard Interrupt"


# Can't support typing.Union[Status, int]
UnionStatus = _StatusConstructor(
    "UnionStatus",
    [(i.name, (i.value, i.phrase, i.description)) for i in chain(HTTPStatus, ResultStatus)],
)


class _BaseResponse(dict):
    __slots__ = (
        "code",
        "msg",
        "data",
    )
    ENUM_TYPE = IntEnum

    def __new__(cls, *args: Any, **kwargs: Any):
        is_valid_kwargs = set(kwargs.keys()).issubset(cls.__slots__)
        if not is_valid_kwargs:
            raise KeyError(f"{cls} only accept kwargs: {cls.__slots__}. Got: {args}, {kwargs}")
        return super().__new__(cls, *args, **kwargs)

    def __init__(
        self,
        code: Union[int, ENUM_TYPE] = 0,
        msg: Optional[Union[str, BaseException]] = None,
        data: Optional[Any] = None,
        **kwargs: Dict[str, Any],
    ):
        kwargs = self.check_kwargs(code, msg, data)
        super().__init__(kwargs)
        for attr in self.__slots__:
            setattr(self, attr, self.get(attr, None))

    def __setitem__(self, key: str, val: Any):
        if not self.__slots__.__contains__(key):
            raise KeyError(f"'{self.__class__.__name__}' object has not allowed attribute '{key}'")
        super().__setitem__(key, val)

    def __eq__(self, __value: object) -> bool:
        return __value in self.values()

    def __ne__(self, __value: object) -> bool:
        return __value not in self.values()

    def check_kwargs(
        self,
        code: Union[int, ENUM_TYPE] = 0,
        msg: Optional[Union[str, BaseException]] = None,
        data: Optional[Any] = None,
    ):
        if isinstance(code, int):
            code = self.ENUM_TYPE(code)
        return {"code": code, "msg": msg or getattr(code, "phrase", ""), "data": data}


class Result(_BaseResponse):
    """API general response class.

    e.g.
        response = Result()
        response = Result(code=100)
        Result(code=100, msg='Hello', data={'a': 1, 'b': 2})
        print(response)
    """

    ENUM_TYPE = ResultStatus


class Response(_BaseResponse):
    """HTTP response class."""

    ENUM_TYPE = HTTPStatus

    def check_kwargs(
        self,
        code: Union[int, ENUM_TYPE] = 0,
        msg: Optional[Union[str, BaseException]] = None,
        data: Optional[Any] = None,
    ):
        if data is None:
            data = {}
        if not isinstance(data, (dict, list)):
            raise TypeError(f"{self.__class__} data must be dict or list. Got: {type(data)}")
        return super().check_kwargs(code, msg, data)


if __name__ == "__main__":
    assert 0 in ResultStatus.__members__.values()
    assert 1 in ResultStatus.__members__.values()
    assert ResultStatus.SUCCESS == 0
    assert ResultStatus.SUCCESS.value == 0
    assert ResultStatus.SUCCESS.phrase == "Success"
    assert ResultStatus.SUCCESS.description == "Success"
    _ = ResultStatus(0)
    # _ = ResultStatus(200, phrase="abc")
    print(type(_), _, _.phrase, _.description)
    assert _ == 0
    assert _ == "Success"
    assert _ == ResultStatus.SUCCESS
    assert _ == ResultStatus.SUCCESS.value
    assert _.value == 0
    assert _.phrase == "Success"
    assert _.description == "Success"
    result = Result()
    print(result)
    result = Result(
        code=600,
        msg="abc",
    )
    # result = Result(code=100, msg='Hello', data={'a': 1, 'b': 2})
    result["data"] = {"c": 1, "d": 2}
    print(result)

    response = Response(200)
    print(response)
