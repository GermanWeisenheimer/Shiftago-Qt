from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, TypeAlias, cast
from PyQt5.QtCore import QObject, pyqtSignal, pyqtBoundSignal, pyqtSlot


@dataclass(frozen=True)
class AppEvent:
    pass


class AppEventEmitter:

    class _QObject(QObject):

        event_signal = pyqtSignal(AppEvent)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._qobject = self._QObject()

    @property
    def app_event_signal(self) -> pyqtBoundSignal:
        return self._qobject.event_signal

    def emit(self, event: AppEvent) -> None:
        self.app_event_signal.emit(event)


AppEventSlot: TypeAlias = Callable[[AppEvent], None]


class Controller(ABC):

    class _QObject(QObject):

        def __init__(self, slot_delegate: AppEventSlot) -> None:
            super().__init__()
            self._slot_delegate = slot_delegate

        @pyqtSlot(AppEvent)
        def on_app_event(self, event: AppEvent) -> None:
            self._slot_delegate(event)

    def __init__(self, parent: Optional['Controller'], view: AppEventEmitter) -> None:
        super().__init__()

        def on_app_event(event: AppEvent) -> None:
            if not self.handle_event(event):
                if parent is not None:
                    parent.handle_event(event)
                else:
                    raise ValueError(f"Unexpected event: {event}")

        self._parent: Optional['Controller'] = parent
        self._app_event_receiver = self._QObject(on_app_event)
        self.connect_with(view)

    @property
    def parent(self) -> Optional['Controller']:
        return self._parent

    def connect_with(self, event_emitter: AppEventEmitter):
        event_emitter.app_event_signal.connect(cast(AppEventSlot, self._app_event_receiver.on_app_event))

    @abstractmethod
    def handle_event(self, event: AppEvent) -> bool:
        raise NotImplementedError
