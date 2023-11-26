from typing import Union, Callable, TypeAlias
from PyQt5.QtCore import pyqtBoundSignal

QtSlot: TypeAlias = Union[Callable[..., None], pyqtBoundSignal]
