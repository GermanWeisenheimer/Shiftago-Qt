import sys
from typing import Type, Generic
from shiftago.core import ShiftagoT, ShiftagoDeser
import tests.data
if sys.version_info < (3, 7, 0):
    import importlib_resources as pkg_resources  # use backport
else:
    import importlib.resources as pkg_resources

class TestDataLoader(Generic[ShiftagoT]):
    def __init__(self, shiftago_cls: Type[ShiftagoT], resource: pkg_resources.Resource):
        self._shiftago_cls = shiftago_cls
        self._resource = resource

    def __enter__(self) -> ShiftagoT:
        with pkg_resources.open_text(tests.data, self._resource) as text_io:
            return ShiftagoDeser(self._shiftago_cls).deserialize(text_io)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_value is not None:
            raise exc_value
