from dataclasses import dataclass
from shiftago.core import Side, Slot, Move
from .hmvc import AppEvent


@dataclass(frozen=True)
class MoveSelectedEvent(AppEvent):
    move: Move


@dataclass(frozen=True)
class AnimationFinishedEvent(AppEvent):
    pass


@dataclass(frozen=True)
class ExitRequestedEvent(AppEvent):
    pass


@dataclass(frozen=True)
class MarbleShiftedEvent(AppEvent):
    slot: Slot
    direction: Side


@dataclass(frozen=True)
class MarbleInsertedEvent(AppEvent):
    slot: Slot
