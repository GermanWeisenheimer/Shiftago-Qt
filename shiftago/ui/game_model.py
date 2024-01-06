from typing import Optional, Tuple
from enum import Enum
from abc import ABC, abstractmethod
from shiftago.app_config import ShiftagoQtConfig
from shiftago.core import Colour, Slot, Side, Move, GameOverCondition, ShiftagoObserver
from shiftago.core.express import ShiftagoExpress
from shiftago.core.express_ai import AlphaBetaPruning
from .hmvc import AppEventEmitter
from .app_events import MarbleShiftedEvent, MarbleInsertedEvent


class PlayerNature(Enum):

    HUMAN = 1
    ARTIFICIAL = 2


class Player:

    def __init__(self, colour: Colour, nature: PlayerNature) -> None:
        self._colour = colour
        self._nature = nature

    @property
    def colour(self) -> Colour:
        return self._colour

    @property
    def nature(self) -> PlayerNature:
        return self._nature


class BoardViewModel(AppEventEmitter, ABC, ShiftagoObserver):

    def __init__(self, players: Tuple[Player, Player]) -> None:
        super().__init__()
        self._players = players

    def player_of(self, colour: Colour) -> Player:
        return next(filter(lambda p: p.colour is colour, self._players))

    def notify_marble_shifted(self, slot: Slot, direction: Side):
        self.emit(MarbleShiftedEvent(slot, direction))

    def notify_marble_inserted(self, slot: Slot):
        self.emit(MarbleInsertedEvent(slot))

    @property
    @abstractmethod
    def current_player(self) -> Optional[Player]:
        pass

    @property
    @abstractmethod
    def game_over_condition(self) -> Optional[GameOverCondition]:
        pass

    @abstractmethod
    def count_occupied_slots(self) -> int:
        pass

    @abstractmethod
    def colour_at(self, position: Slot) -> Optional[Colour]:
        pass

    @abstractmethod
    def is_insertion_possible(self, side: Side, insert_pos: int) -> bool:
        pass


class ShiftagoExpressModel(BoardViewModel):

    def __init__(self, players: Tuple[Player, Player], app_config: ShiftagoQtConfig) -> None:
        super().__init__(players)
        core_model = ShiftagoExpress((players[0].colour, players[1].colour))
        core_model.observer = self
        self._core_model = core_model
        self._ai_engine = AlphaBetaPruning(app_config.ai_engine_skill_level)

    @property
    def current_player(self) -> Optional[Player]:
        current_colour = self._core_model.current_player
        return self.player_of(current_colour) if current_colour is not None else None

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._core_model.game_over_condition

    def count_occupied_slots(self) -> int:
        return self._core_model.count_occupied_slots()

    def colour_at(self, position: Slot) -> Optional[Colour]:
        return self._core_model.colour_at(position)

    def is_insertion_possible(self, side: Side, insert_pos: int) -> bool:
        return self._core_model.find_first_empty_slot(side, insert_pos) is not None

    def apply_move(self, move: Move) -> Optional[GameOverCondition]:
        self._core_model.apply_move(move)

    def ai_select_move(self) -> Move:
        return self._ai_engine.select_move(self._core_model)
