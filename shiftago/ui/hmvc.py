from abc import ABC
from typing import Optional, Callable, TypeAlias, cast
from PyQt5.QtCore import QObject, pyqtSignal, pyqtBoundSignal, pyqtSlot


class AppEvent(ABC):  # pylint: disable= too-few-public-methods
    pass


class AppEventEmitter:

    class SignalWrapper(QObject):

        event_signal = pyqtSignal(AppEvent)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._signal_wrapper = self.SignalWrapper()

    @property
    def app_event_signal(self) -> pyqtBoundSignal:
        return self._signal_wrapper.event_signal

    def emit(self, event: AppEvent) -> None:
        self.app_event_signal.emit(event)


AppEventSlot: TypeAlias = Callable[[AppEvent], None]


class Controller(QObject):

    def __init__(self, parent: Optional['Controller'], view: AppEventEmitter) -> None:
        super().__init__()
        self._parent: Optional['Controller'] = parent
        self.connect_with(view)

    @property
    def parent(self) -> Optional['Controller']:
        return self._parent

    def connect_with(self, event_emitter: AppEventEmitter):
        event_emitter.app_event_signal.connect(cast(AppEventSlot, self._on_app_event))

    @pyqtSlot(AppEvent)
    def _on_app_event(self, event: AppEvent) -> None:
        if not self.handle_event(event):
            if self._parent:
                self._parent.handle_event(event)
            else:
                raise ValueError(f"Unexpected event: {event}")

    def handle_event(self, event: AppEvent) -> bool:
        raise NotImplementedError
