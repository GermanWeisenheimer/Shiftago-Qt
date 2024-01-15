import sys
from typing import Type, TypeVar, Generic
from shiftago.core import Shiftago
import tests.data
if sys.version_info < (3, 7, 0):
    import importlib_resources as pkg_resources  # use backport
else:
    import importlib.resources as pkg_resources

_S = TypeVar("_S", bound=Shiftago)

class TestDataLoader(Generic[_S]):
    def __init__(self, shiftago_cls: Type[_S], resource: pkg_resources.Resource):
        self._shiftago_cls = shiftago_cls
        self._resource = resource

    def __enter__(self) -> _S:
        with pkg_resources.open_text(tests.data, self._resource) as text_io:
            return self._shiftago_cls.deserialize(text_io)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is not None:
            raise exc_value
