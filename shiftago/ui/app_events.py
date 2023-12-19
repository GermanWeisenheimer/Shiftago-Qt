from dataclasses import dataclass
from shiftago.core import Side, Slot, Move
from .hmvc import AppEvent


@dataclass(frozen=True)
class MoveSelectedEvent(AppEvent):
    """Emitted by view and thinking worker."""
    move: Move


@dataclass(frozen=True)
class AnimationFinishedEvent(AppEvent):
    """Emitted by view."""


@dataclass(frozen=True)
class ExitRequestedEvent(AppEvent):
    """Emitted by view."""


@dataclass(frozen=True)
class MarbleShiftedEvent(AppEvent):
    """Emitted by model."""
    slot: Slot
    direction: Side


@dataclass(frozen=True)
class MarbleInsertedEvent(AppEvent):
    """Emitted by model."""
    slot: Slot
