from types import MethodType
from typing import Callable


__all__ = [
    "check_method_bound_to",
]


def check_method_bound_to(method: Callable):
    """Check if a method is bound to a class or an object.
    If it is bound to a class, return True and the class it is bound to.
    If it is bound to an object, return True and the object it is bound to.
    Otherwise, return False and None.
    """
    if not isinstance(method, MethodType):
        return False, None
    __self__ = getattr(method, "__self__", None)
    assert not __self__ is None
    assert isinstance(__self__, object)
    if isinstance(__self__, type):
        name = method.__name__
        for cls in __self__.__mro__:
            descriptor = vars(cls).get(name)
            if descriptor is not None:
                return isinstance(descriptor, classmethod), cls
    return True, __self__
