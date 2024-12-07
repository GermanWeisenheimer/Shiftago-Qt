from dataclasses import dataclass
from shiftago.core import Side, Slot, Colour, Move
from shiftago.ui import AppEvent


@dataclass(frozen=True)
class ReadyForFirstMoveEvent(AppEvent):
    """Emitted by view."""


@dataclass(frozen=True)
class MoveSelectedEvent(AppEvent):
    """Emitted by view and thinking worker."""
    move: Move


@dataclass(frozen=True)
class AnimationFinishedEvent(AppEvent):
    """Emitted by view."""


@dataclass(frozen=True)
class NewGameRequestedEvent(AppEvent):
    """Emitted by view when a new game is requested."""


@dataclass(frozen=True)
class ScreenshotRequestedEvent(AppEvent):
    """Emitted by view when a screenshot is requested."""


@dataclass(frozen=True)
class ExitRequestedEvent(AppEvent):
    """Emitted by view when exiting is requested."""


@dataclass(frozen=True)
class MarbleShiftedEvent(AppEvent):
    """Emitted by model when a marble is shifted."""
    slot: Slot
    direction: Side


@dataclass(frozen=True)
class MarbleInsertedEvent(AppEvent):
    """Emitted by model when a marble is inserted."""
    slot: Slot
    colour: Colour


@dataclass(frozen=True)
class BoardResetEvent(AppEvent):
    """Emitted by model when the board is reset."""
