from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, TypeAlias
from PyQt5.QtCore import QObject, pyqtSignal


@dataclass(frozen=True)
class AppEvent:
    pass


AppEventHandler: TypeAlias = Callable[[AppEvent], None]


class AppEventEmitter:

    class _QObject(QObject):

        event_signal = pyqtSignal(AppEvent)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._qobject = self._QObject()

    def connect_with(self, handler: AppEventHandler):
        self._qobject.event_signal.connect(handler)

    def emit(self, event: AppEvent) -> None:
        self._qobject.event_signal.emit(event)


class Controller(ABC):

    class _QObject(QObject):

        def __init__(self, event_handler: AppEventHandler) -> None:
            super().__init__()
            self._event_handler = event_handler

        def connect_with(self, event_emitter: AppEventEmitter):
            event_emitter.connect_with(self._event_handler)

    def __init__(self, parent: Optional['Controller'], view: AppEventEmitter) -> None:
        super().__init__()

        def event_handler(event: AppEvent) -> None:
            if not self.handle_event(event):
                if parent is not None:
                    parent.handle_event(event)
                else:
                    raise ValueError(f"Unexpected event: {event}")

        self._parent: Optional['Controller'] = parent
        self._qobject = self._QObject(event_handler)
        self.connect_with(view)

    @property
    def parent(self) -> Optional['Controller']:
        return self._parent

    def connect_with(self, event_emitter: AppEventEmitter):
        self._qobject.connect_with(event_emitter)

    @abstractmethod
    def handle_event(self, event: AppEvent) -> bool:
        raise NotImplementedError
