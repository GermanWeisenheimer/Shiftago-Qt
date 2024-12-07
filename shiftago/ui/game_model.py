import random
from typing import Optional, Tuple, Sequence, Set, override
from enum import Enum
from abc import ABC, abstractmethod
from shiftago.app_config import ShiftagoConfig
from shiftago.core import Colour, Slot, Side, Move, GameOverCondition, MoveObserver
from shiftago.core.express import ShiftagoExpress, SlotsInLine
from shiftago.core.express_ai import SkillLevel, AlphaBetaPruning
from shiftago.ui import AppEventEmitter
from .app_events import MarbleShiftedEvent, MarbleInsertedEvent, BoardResetEvent


class PlayerNature(Enum):
    """
    PlayerNature is an enumeration representing the nature of a player.

    Attributes:
    HUMAN (int): Represents a human player.
    ARTIFICIAL (int): Represents an AI player.
    """
    HUMAN = 1
    ARTIFICIAL = 2


class Player:
    """
    Player represents a player in the game, defined by their colour and nature (human or AI).
    """

    def __init__(self, colour: Colour, nature: PlayerNature) -> None:
        """
        Initializes a Player with the given colour and nature.
        """
        self._colour = colour
        self._nature = nature

    def __str__(self) -> str:
        """
        Returns a string representation of the Player.
        """
        return f"Player(colour = {self._colour.name}, nature = {self.nature.name})"

    @property
    def colour(self) -> Colour:
        """
        Returns the colour of the player.
        """
        return self._colour

    @property
    def nature(self) -> PlayerNature:
        """
        Returns the nature of the player.
        """
        return self._nature


class BoardViewModel(AppEventEmitter, ABC, MoveObserver):
    """
    BoardViewModel is an abstract base class that represents the view model for the game board.
    It extends AppEventEmitter to emit events and MoveObserver to observe move events.
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    @abstractmethod
    def players(self) -> Tuple[Player, ...]:
        """
        Returns the players in the game. They are ordered in the sequence of their turns.
        """

    @property
    @abstractmethod
    def whose_turn_it_is(self) -> Player:
        """
        Returns the player whose turn it is to make a move.
        """

    @property
    @abstractmethod
    def game_over_condition(self) -> Optional[GameOverCondition]:
        """
        Returns the condition of the game if it is over. If the game is not over,
        it returns None.
        """

    @override
    def notify_marble_shifted(self, slot: Slot, direction: Side):
        """
        Notifies the view that a marble has been shifted in the direction of the given side.
        """
        self.emit(MarbleShiftedEvent(slot, direction))

    @override
    def notify_marble_inserted(self, slot: Slot):
        """
        Notifies the view that a marble has been inserted into the specified slot.
        """
        colour = self.colour_at(slot)
        assert colour is not None, f"{slot} is not occupied!"
        self.emit(MarbleInsertedEvent(slot, colour))

    def notify_board_reset(self):
        """
        Notifies the view that the board been has been reset.
        """
        self.emit(BoardResetEvent())

    def player_of(self, colour: Colour) -> Player:
        """
        Returns the player with the specified colour.
        """
        return next(filter(lambda p: p.colour is colour, self.players))

    @abstractmethod
    def count_occupied_slots(self) -> int:
        """
        Returns the number of occupied slots on the game board.
        """

    @abstractmethod
    def colour_at(self, position: Slot) -> Optional[Colour]:
        """
        Returns the colour of the marble at the specified slot position on the game board.
        If the slot is unoccupied, it returns None.
        """

    @abstractmethod
    def is_insertion_possible(self, side: Side, insert_pos: int) -> bool:
        """
        Checks if it is possible to insert a marble at the specified position on the given side of the board.
        """


class ShiftagoExpressModel(BoardViewModel):
    """
    ShiftagoExpressModel is a concrete implementation of BoardViewModel for the Express variant
    of the game. It manages the game state, players, and interactions with the core game logic.
    """

    def __init__(self, players: Tuple[Player, Player], config: ShiftagoConfig) -> None:
        """
        Initializes the ShiftagoExpressModel with the given players and configuration.
        """
        super().__init__()
        self._players = players
        core_model = ShiftagoExpress(colours=self._randomize_player_sequence())
        self._core_model = core_model
        self._ai_engine = AlphaBetaPruning(config.skill_level)

    @property
    @override
    def players(self) -> Tuple[Player, Player]:
        return self._players

    @property
    @override
    def whose_turn_it_is(self) -> Player:
        return self.player_of(self._core_model.colour_to_move)

    @property
    def skill_level(self) -> SkillLevel:
        return self._ai_engine.skill_level

    @property
    @override
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._core_model.game_over_condition

    def winning_lines_of_winner(self) -> Set[SlotsInLine]:
        """
        Returns the winning lines of the winner if the game is over and there is a winner.
        Raises:
        AssertionError: If the game is not over or there is no winner.
        """
        return self._core_model.winning_lines_of_winner()

    def _randomize_player_sequence(self) -> Sequence[Colour]:
        """
        Randomizes the sequence of players to determine the order of turns.
        """
        colours = [self._players[0].colour, self._players[1].colour]
        random.shuffle(colours)
        return colours

    def reset(self) -> None:
        """
        Resets the game by randomizing the player sequence and notifying the view that
        the board has been reset.
        """
        self._core_model.colours = self._randomize_player_sequence()
        self.notify_board_reset()

    @override
    def count_occupied_slots(self) -> int:
        return self._core_model.count_occupied_slots()

    @override
    def colour_at(self, position: Slot) -> Optional[Colour]:
        return self._core_model.colour_at(position)

    @override
    def is_insertion_possible(self, side: Side, insert_pos: int) -> bool:
        return self._core_model.find_first_empty_slot(side, insert_pos) is not None

    def apply_move(self, move: Move) -> Optional[GameOverCondition]:
        """
        Applies the given move to the game board and updates the game state. If the game is over
        as a result of the move, it returns the game over condition. Otherwise, it returns None.
        """
        self._core_model.apply_move(move, self)

    def ai_select_move(self) -> Move:
        """
        Selects the best move for the AI based on the current game state.
        """
        return self._ai_engine.select_move(self._core_model)
