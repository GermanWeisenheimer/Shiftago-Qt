from typing import Optional
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod
from shiftago.core import Colour, Slot, Side, ShiftagoObserver
from shiftago.core.express import ShiftagoExpress
from shiftago.ui import AppEvent, AppEventEmitter


class PlayerNature(Enum):

    HUMAN = 1
    ARTIFICIAL = 2


@dataclass(frozen=True)
class MarbleShiftedEvent(AppEvent):
    slot: Slot
    direction: Side


@dataclass(frozen=True)
class MarbleInsertedEvent(AppEvent):
    slot: Slot


class BoardViewModel(AppEventEmitter, ABC, ShiftagoObserver):

    def __init__(self, core_model: ShiftagoExpress) -> None:
        super().__init__()
        core_model.observer = self
        self._core_model = core_model

    @property
    def current_player(self) -> Optional[Colour]:
        return self._core_model.current_player

    @property
    def current_player_nature(self) -> Optional[PlayerNature]:
        if self._core_model.current_player is not None:
            return self.player_nature_of(self._core_model.current_player)
        return None

    @abstractmethod
    def player_nature_of(self, colour: Colour) -> PlayerNature:
        pass

    def colour_at(self, position: Slot) -> Optional[Colour]:
        return self._core_model.colour_at(position)

    def is_insertion_possible(self, side: Side, insert_pos: int) -> bool:
        return self._core_model.find_first_empty_slot(side, insert_pos) is not None

    def notify_marble_shifted(self, slot: Slot, direction: Side):
        self.emit(MarbleShiftedEvent(slot, direction))

    def notify_marble_inserted(self, slot: Slot):
        self.emit(MarbleInsertedEvent(slot))
