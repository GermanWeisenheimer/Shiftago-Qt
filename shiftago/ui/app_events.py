from dataclasses import dataclass
from shiftago.core import Move


@dataclass(frozen=True)
class AppEvent:
    pass


@dataclass(frozen=True)
class MoveSelectedEvent(AppEvent):
    move: Move


@dataclass(frozen=True)
class AnimationFinishedEvent(AppEvent):
    pass


@dataclass(frozen=True)
class ExitRequestedEvent(AppEvent):
    pass
