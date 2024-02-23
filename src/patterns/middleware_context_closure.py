'''
Design Pattern: Middleware. A middleware is a function that wraps around a core function.
设计模式: 中间件
'''
import functools
from typing import Any, Callable, Dict, List, Tuple

from utils.method import check_method_bound_to


class Context:
    '''Context is a class that wraps around the arguments of a Middleware function.
    It also provides a next function that can be called to call the next middleware.
    in the chain. The next function is initialized to a dummy function that does nothing. That is, the closure around the next middleware.
    In this case, Mainly used to store contextual of the current call, and pass it to the next middleware.
    '''
    _args: Tuple[Any, ...]
    _kwargs: Dict[str, Any]

    def __init__(self, *args, **kwargs):
        # _next: Next middleware or core function
        self._next: Callable[..., Any] = lambda *args, **kwargs: None
        # self._args: Tuple[Any, ...] = tuple()
        # self._kwargs: Dict[str, Any] = dict()
        self.args: Tuple[Any, ...] = args
        self.kwargs: Dict[str, Any] = kwargs
        # self.set_args(args)

    # args = property(lambda self: self._args) # type: ignore
    # kwargs = property(lambda self: self._kwargs) # type: ignore

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, args: Tuple[Any, ...]):
        if not isinstance(args, tuple):
            raise TypeError(f"args must be tuple, not {type(args)}")
        self._args = args

    @property
    def kwargs(self):
        return self._kwargs

    @kwargs.setter
    def kwargs(self, kwargs):
        if not isinstance(kwargs, dict):
            raise TypeError(f"kwargs must be dict, not {type(kwargs)}")
        self._kwargs = kwargs

    @property
    def next(self):
        return self._next

    @next.setter
    def next(self, next):
        self._next = next


class MiddlewareScheduler():
    '''Middleware closure implementation
    MiddlewareSchedule is a class that encapsulates all middlewares and core functions based on closures.
    Use Context to pass contextual data between each middleware function.
    It provides a method to add middleware and core functions.
    It also provides a method to initialize the scheduler. The initialization process will wrap all core functions with middlewares. The wrapped functions will be added to the scheduler as attributes.

    Can be used for functions, instance methods, and class methods.

    TODO: Calling ctx.next() within the core function will occur loop.
    '''
    def __init__(self):
        # All middlewares
        self._middlewares: List[Callable[..., Any]] = []
        # All core functions
        self._functions: Dict[str, Callable[..., Any]] = {}

    def add_middleware(self, middleware_func: Callable[..., Any]) -> Callable[..., Any]:
        '''Add middleware to scheduler. The middleware will be called in reversed order.
        Adapt to both function and classmethod.
        '''
        @functools.wraps(middleware_func)
        def wrapper(*args: Any, ctx, **kwargs: Any) -> Any:
            # If middleware_func is a instance method or classmethod, then the first argument is self or cls.
            _ismethod, _self_or_cls = check_method_bound_to(middleware_func)
            if _ismethod:
                return middleware_func(_self_or_cls, *args, ctx=ctx, **kwargs)
            return middleware_func(*args, ctx=ctx, **kwargs)
        self._middlewares.append(wrapper)
        return wrapper

    def add_func(self, name: str) -> Callable[..., Any]:
        def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
            self._functions.setdefault(name, func)
            return func
        return decorate

    def _load_middleware(self, ctx: Context, func: Callable[..., Any]) -> Callable[..., Any]:
        def next(*args, **kwargs):
            return func(*args, ctx=ctx, **kwargs)
        for middleware in reversed(self._middlewares):
            # using closure to wrap middleware
            # @functools.wraps(middleware)
            def f(middleware=middleware, next=next):
                # @functools.wraps(middleware)
                def new_next(*args, **kwargs):
                    ctx.next = next
                    return middleware(*ctx.args, ctx=ctx, **ctx.kwargs)
                # new_next.__name__ = getattr(middleware, '__name__')
                return new_next
            next = f()
        return next

    def _wrap(self, func: Callable[..., Any]) -> Callable[..., Any]:
        def f(*args, **kwargs):
            ctx = Context(*args, **kwargs)
            return self._load_middleware(ctx, func)(
                *args, **kwargs
            )
        return f

    # def initialize(self, *args: Tuple[Any, ...], **kwargs: Dict[str, Any]):
    def initialize(self):
        for name, func in self._functions.items():
            self.__setattr__(name, self._wrap(func))
            # self._wrap(func)()


if __name__ == '__main__':
    scheduler = MiddlewareScheduler()

    # @scheduler.add_middleware
    def the_1nd_middleware(*args, ctx: Context, **kwargs):
        print('1' * 20)
        print("The first one", ctx.__dict__)
        print("The first one", args, kwargs)
        return ctx.next(*args, **kwargs)

    scheduler.add_middleware(the_1nd_middleware)


    class Obj:
        # @classmethod
        def the_2nd_middleware(cls, *args: Tuple[Any, ...], ctx: Context, **kwargs: Dict[str, Any]):
            print('2' * 20)
            print("The 2nd one", cls, ctx)
            print("The 2nd one", ctx.__dict__)
            print("The 2nd one", args, kwargs)
            return ctx.next(cls, *ctx.args, **ctx.kwargs)

    obj = Obj()

    scheduler.add_middleware(Obj.the_2nd_middleware)
    scheduler.add_middleware(obj.the_2nd_middleware)

    @scheduler.add_func('core_func')
    def core_func(*args, ctx: Context, **kwargs):
        return "The Core Function"


    @scheduler.add_func('core_func2')
    def core_func2(*args, ctx, **kwargs):
        print('core_func2', ctx)
        return "The Core Function2"


    result = scheduler.initialize()
    # print(result)
    print(getattr(scheduler, 'core_func')('a', 'b', c='c'))
    # print(getattr(obj, 'core_func')('a', 'b', 'd', c='c'))
    # print(scheduler.core_func2('a', 'b', c='c'))
