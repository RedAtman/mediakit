from enum import IntEnum
from http import HTTPStatus
from itertools import chain
from typing import Any, Optional, Union


class _StatusConstructor(IntEnum):
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


Status = _StatusConstructor(
    "ResultStatus",
    [
        (i.name, (i.value, i.phrase, i.description))
        for i in chain(HTTPStatus, ResultStatus)
    ],
)


class BaseResponse(dict):
    __slots__ = (
        "code",
        "msg",
        "data",
    )

    def __new__(cls, *args: Any, **kwargs: Any):
        is_valid_kwargs = set(kwargs.keys()).issubset(cls.__slots__)
        if not is_valid_kwargs:
            raise KeyError(
                f"{cls} only accept kwargs: {cls.__slots__}. Got: {args}, {kwargs}"
            )
        return super().__new__(cls, *args, **kwargs)

    def __init__(
        self,
        code: int = 0,
        msg: Optional[Union[str, Exception]] = None,
        data: Optional[Any] = None,
        **kwargs: Any,
    ):
        kwargs = self.check_kwargs(code, msg, data)
        super().__init__(kwargs)
        for attr in self.__slots__:
            setattr(self, attr, self.get(attr, None))

    def __setitem__(self, key: str, val: Any):
        if not self.__slots__.__contains__(key):
            raise KeyError(
                f"'{self.__class__.__name__}' object has not allowed attribute '{key}'"
            )
        super().__setitem__(key, val)

    def __eq__(self, __value: object) -> bool:
        return __value in self.values()

    def check_kwargs(
        self,
        code: Union[int, Status] = 0,
        msg: Optional[str] = None,
        data: Optional[Any] = None,
    ):
        if isinstance(code, int):
            code = Status(code)
        return {"code": code, "msg": msg or code.phrase, "data": data}


class Result(BaseResponse):
    """API general response class.

    e.g.
        response = Result()
        response = Result(code=100)
        Result(code=100, msg='Hello', data={'a': 1, 'b': 2})
        print(response)
    """

    pass


class Response(BaseResponse):

    def check_kwargs(
        self,
        code: Union[int, Status] = 0,
        msg: Optional[str] = None,
        data: Optional[Any] = None,
    ):
        kwargs = super().check_kwargs(code, msg, data)
        data = kwargs.get("data")
        if not isinstance(data, (dict, list)):
            raise TypeError(
                f"{self.__class__} data must be dict or list. Got: {type(data)}"
            )
        return kwargs


if __name__ == "__main__":
    assert 0 in Status.__members__.values()
    assert 200 in Status.__members__.values()
    assert Status.SUCCESS == 0
    assert Status.SUCCESS.value == 0
    assert Status.SUCCESS.phrase == "Success"
    assert Status.SUCCESS.description == "Success"
    _ = Status(0)
    # _ = ResultStatus(200, phrase='abc')
    print(type(_), _, _.phrase, _.description)
    assert _ == 0
    assert _ == "Success"
    assert _ == Status.SUCCESS
    assert _ == Status.SUCCESS.value
    assert _.value == 0
    assert _.phrase == "Success"
    assert _.description == "Success"
    # response = Result()
    response = Result(
        code=600,
        msg="abc",
        # dd=1,
    )
    # response = Result(code=100, msg='Hello', data={'a': 1, 'b': 2})
    response["data"] = {"c": 1, "d": 2}
    print(response)
