from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, TypeAlias, cast
from importlib.resources import path as resrc_path
from PySide6.QtCore import QObject, Signal, SignalInstance
from PySide6.QtGui import QPixmap
import shiftago.ui.images


def load_image(image_resource: str) -> QPixmap:
    """
    Loads an image resource and returns it as a QPixmap object.
    """
    with resrc_path(shiftago.ui.images, image_resource) as path:
        return QPixmap(str(path))


@dataclass(frozen=True)
class AppEvent:
    """
    AppEvent is a base class for application events. It is used to represent events that occur within the application.
    """


# Type alias for a function that handles AppEvent objects
AppEventHandler: TypeAlias = Callable[[AppEvent], None]


class AppEventEmitter:
    """
    AppEventEmitter is responsible for emitting application events to connected handlers.
    It uses Qt's signal-slot mechanism to manage event handling.
    """

    class _QObject(QObject):
        """
        _QObject is used internally as delegate to emit event signals.
        """
        event_signal = Signal(AppEvent)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._qobject = self._QObject()

    def connect_with(self, handler: AppEventHandler):
        """
        Connects the given handler to the event emitter.
        """
        cast(SignalInstance, self._qobject.event_signal).connect(handler)

    def emit(self, event: AppEvent) -> None:
        """
        Emits the given event to all connected handlers.
        """
        cast(SignalInstance, self._qobject.event_signal).emit(event)


class Controller(ABC):
    """
    Controller is an abstract base class for controllers that handle application events.
    It provides a mechanism to handle events and delegate them to a parent controller if necessary.
    """

    def __init__(self, parent: Optional['Controller'], view: AppEventEmitter) -> None:
        """
        Initializes the Controller with an optional parent controller and view.
        """
        self._app_event_emitter: Optional[AppEventEmitter] = None
        if parent is not None:
            self._app_event_emitter = AppEventEmitter()
            parent.connect_with(self._app_event_emitter)
        self.connect_with(view)

    def connect_with(self, event_emitter: AppEventEmitter):
        """
        Connects the controller with the given event emitter. This method sets up an event handler
        that processes events and delegates them to the parent controller if necessary.
        """
        def handle_event(event: AppEvent) -> None:
            if not self.handle_event(event):
                if self._app_event_emitter is not None:
                    self._app_event_emitter.emit(event)  # delegate handling to parent
                else:
                    raise ValueError(f"Unexpected event: {event}")

        event_emitter.connect_with(handle_event)

    @abstractmethod
    def handle_event(self, event: AppEvent) -> bool:
        """
        Abstract method to handle the given event. Subclasses must implement this method.

        Returns:
        True if the event was handled, False otherwise.
        """
