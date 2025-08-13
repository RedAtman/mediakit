from typing import Any


class CallHookMetaClass(type):
    """Hook __call__ method to call __after_init__ method after __init__ method."""

    def __call__(cls: "CallHookMetaClass", *args, **kwargs):
        print("before __call__")
        instance = type.__call__(cls, *args, **kwargs)
        instance.__after_init__()
        print("after __call__")
        return instance


class Singleton(type):
    """Singleton class implementation. Keep only one instance of the class."""

    _mapper_cls_instance: dict[Any, Any] = {}

    def __call__(cls: "Singleton", *args, **kwargs):
        if cls not in cls._mapper_cls_instance:
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            cls._mapper_cls_instance[cls] = instance
        return cls._mapper_cls_instance[cls]


if __name__ == "__main__":

    class A(metaclass=CallHookMetaClass):

        def __new__(cls):
            print("__new__")
            return super().__new__(cls)

        def __init__(self):
            print("__init__")
            self.a = 1

        def __before_init__(self):
            print("before __init__")

        def __after_init__(self):
            print("after __init__")

    a = A()
    print(a.a)

    class B(metaclass=Singleton):
        def __init__(self, name):
            self.name = name

    b1 = B("b1")
    b2 = B("b2")
    print(b1.name, b2.name)
    print(b1 is b2)
