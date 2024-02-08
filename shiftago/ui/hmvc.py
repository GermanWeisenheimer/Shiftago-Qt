from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, TypeAlias, cast
from PySide2.QtCore import QObject, Signal, SignalInstance


@dataclass(frozen=True)
class AppEvent:
    pass


AppEventHandler: TypeAlias = Callable[[AppEvent], None]


class AppEventEmitter:

    class _QObject(QObject):

        event_signal = Signal(AppEvent)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._qobject = self._QObject()

    def connect_with(self, handler: AppEventHandler):
        cast(SignalInstance, self._qobject.event_signal).connect(handler)

    def disconnect_from(self, handler: AppEventHandler):
        cast(SignalInstance, self._qobject.event_signal).disconnect(handler)

    def emit(self, event: AppEvent) -> None:
        cast(SignalInstance, self._qobject.event_signal).emit(event)


class Controller(ABC):

    def __init__(self, parent: Optional['Controller'], view: AppEventEmitter) -> None:
        self._app_event_emitter: Optional[AppEventEmitter] = None
        if parent is not None:
            self._app_event_emitter = AppEventEmitter()
            parent.connect_with(self._app_event_emitter)
        self.connect_with(view)

    def connect_with(self, event_emitter: AppEventEmitter):
        event_emitter.connect_with(self._handle_event)

    def disconnect_from(self, event_emitter: AppEventEmitter):
        event_emitter.disconnect_from(self._handle_event)

    def _handle_event(self, event: AppEvent) -> None:
        if not self.handle_event(event):
            if self._app_event_emitter is not None:
                self._app_event_emitter.emit(event)  # delegate handling to parent
            else:
                raise ValueError(f"Unexpected event: {event}")

    @abstractmethod
    def handle_event(self, event: AppEvent) -> bool:
        raise NotImplementedError
