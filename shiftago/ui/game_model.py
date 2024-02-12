import random
from typing import Optional, Tuple, Sequence, Set
from enum import Enum
from abc import ABC, abstractmethod
from shiftago.app_config import ShiftagoConfig
from shiftago.core import Colour, Slot, Side, Move, GameOverCondition, ShiftagoObserver
from shiftago.core.express import ShiftagoExpress, WinningLine
from shiftago.core.express_ai import SkillLevel, AlphaBetaPruning
from shiftago.ui import AppEventEmitter
from .app_events import MarbleShiftedEvent, MarbleInsertedEvent, BoardResetEvent


class PlayerNature(Enum):

    HUMAN = 1
    ARTIFICIAL = 2


class Player:

    def __init__(self, colour: Colour, nature: PlayerNature) -> None:
        self._colour = colour
        self._nature = nature

    def __str__(self) -> str:
        return f"Player(colour = {self._colour.name}, nature = {self.nature.name})"

    @property
    def colour(self) -> Colour:
        return self._colour

    @property
    def nature(self) -> PlayerNature:
        return self._nature


class BoardViewModel(AppEventEmitter, ABC, ShiftagoObserver):

    def __init__(self) -> None:
        super().__init__()

    @property
    @abstractmethod
    def players(self) -> Tuple[Player, ...]:
        pass

    @property
    @abstractmethod
    def whose_turn_it_is(self) -> Player:
        pass

    @property
    @abstractmethod
    def game_over_condition(self) -> Optional[GameOverCondition]:
        pass

    def notify_marble_shifted(self, slot: Slot, direction: Side):
        self.emit(MarbleShiftedEvent(slot, direction))

    def notify_marble_inserted(self, slot: Slot):
        self.emit(MarbleInsertedEvent(slot))

    def notify_board_reset(self):
        self.emit(BoardResetEvent())

    def player_of(self, colour: Colour) -> Player:
        return next(filter(lambda p: p.colour is colour, self.players))

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

    def __init__(self, players: Tuple[Player, Player], config: ShiftagoConfig) -> None:
        super().__init__()
        self._players = players
        core_model = ShiftagoExpress(colours=self._randomize_player_sequence())
        core_model.observer = self
        self._core_model = core_model
        self._ai_engine = AlphaBetaPruning(config.skill_level)

    @property
    def players(self) -> Tuple[Player, Player]:
        return self._players

    @property
    def whose_turn_it_is(self) -> Player:
        return self.player_of(self._core_model.colour_to_move)

    @property
    def skill_level(self) -> SkillLevel:
        return self._ai_engine.skill_level

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._core_model.game_over_condition

    def winning_lines_of_winner(self) -> Set[WinningLine]:
        return self._core_model.winning_lines_of_winner()

    def _randomize_player_sequence(self) -> Sequence[Colour]:
        colours = [self._players[0].colour, self._players[1].colour]
        random.shuffle(colours)
        return colours

    def reset(self) -> None:
        self._core_model.colours = self._randomize_player_sequence()
        self.notify_board_reset()

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
