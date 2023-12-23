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

    def __init__(self, parent: Optional['Controller'], view: AppEventEmitter) -> None:
        self._app_event_emitter: Optional[AppEventEmitter] = None
        if parent is not None:
            self._app_event_emitter = AppEventEmitter()
            parent.connect_with(self._app_event_emitter)
        self.connect_with(view)

    def connect_with(self, event_emitter: AppEventEmitter):
        def handle_event(event: AppEvent) -> None:
            if not self.handle_event(event):
                if self._app_event_emitter is not None:
                    self._app_event_emitter.emit(event) # delegate handling to parent
                else:
                    raise ValueError(f"Unexpected event: {event}")

        event_emitter.connect_with(handle_event)

    @abstractmethod
    def handle_event(self, event: AppEvent) -> bool:
        raise NotImplementedError
