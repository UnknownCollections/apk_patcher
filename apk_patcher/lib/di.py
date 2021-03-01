import inspect
from typing import Dict, Type, TypeVar

C = TypeVar('C')
T = TypeVar('T')


def di_class_init(target: Type[T], container: Dict[Type[C], C], *args, **kwargs) -> T:
    di_vars = {}
    params = inspect.signature(target.__init__).parameters.items()
    for name, param in params:
        if param.annotation == inspect.Parameter.empty:
            continue
        if name in kwargs:
            continue
        if param.annotation in container:
            di_vars[name] = container[param.annotation]
    return target(*args, **{
        **di_vars,
        **kwargs
    })
