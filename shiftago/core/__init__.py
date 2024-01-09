# pylint: disable=consider-using-f-string
from typing import List, Tuple, Dict, Deque, Optional, TextIO
from abc import ABC, abstractmethod
from enum import Enum
from collections import namedtuple, defaultdict, deque
from functools import total_ordering
import json
from io import StringIO

NUM_SLOTS_PER_SIDE = 7
NUM_MARBLES_PER_COLOUR = 22


class Colour(Enum):

    BLUE = 'B'
    GREEN = 'G'
    ORANGE = 'O'

    def __str__(self) -> str:
        return self.value


class Side(Enum):

    LEFT = 0, 0, False, 1
    RIGHT = 1, NUM_SLOTS_PER_SIDE - 1, False, -1
    TOP = 2, 0, True, 1
    BOTTOM = 3, NUM_SLOTS_PER_SIDE - 1, True, -1

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: int, position: int, is_horizontal: bool, shift_direction: int):
        if position in (0, NUM_SLOTS_PER_SIDE - 1):
            self._position = position
        else:
            raise ValueError("Illegal position: {0}".format(position))
        self._is_horizontal = is_horizontal
        if shift_direction in (-1, 1):
            self._shift_direction = shift_direction
        else:
            raise ValueError("Illegal shift direction: {0}".format(shift_direction))

    def __str__(self) -> str:
        return self.name

    @property
    def position(self) -> int:
        return self._position

    @property
    def is_horizontal(self) -> bool:
        return self._is_horizontal

    @property
    def is_vertical(self) -> bool:
        return not self._is_horizontal

    @property
    def shift_direction(self) -> int:
        return self._shift_direction

    @property
    def opposite(self) -> 'Side':
        if self == Side.LEFT:
            return Side.RIGHT
        if self == Side.RIGHT:
            return Side.LEFT
        if self == Side.TOP:
            return Side.BOTTOM
        return Side.TOP


@total_ordering
class Slot(namedtuple('Slot', 'hor_pos ver_pos')):

    _instances = []  # type: List[List[Slot]]

    @classmethod
    def initialize(cls):
        if cls.is_initialized():
            raise RuntimeError("Class Slot has already been initialized!")
        cls._instances = [[Slot(hor_pos, ver_pos) for hor_pos in range(NUM_SLOTS_PER_SIDE)]
                          for ver_pos in range(NUM_SLOTS_PER_SIDE)]

    @classmethod
    def is_initialized(cls) -> bool:
        return bool(cls._instances)

    def __new__(cls, hor_pos: int, ver_pos: int):
        if ver_pos < 0 or ver_pos >= NUM_SLOTS_PER_SIDE:
            raise ValueError(
                "Parameter ver_pos has illegal value: {0}".format(ver_pos))
        if hor_pos < 0 or hor_pos >= NUM_SLOTS_PER_SIDE:
            raise ValueError(
                "Parameter hor_pos has illegal value: {0}".format(hor_pos))
        if cls.is_initialized():
            return cls._instances[ver_pos][hor_pos]
        return super().__new__(cls, hor_pos, ver_pos)

    def __str__(self) -> str:
        return "[{0},{1}]".format(self.hor_pos, self.ver_pos)

    def __lt__(self, other) -> bool:
        if self.ver_pos < other.ver_pos:
            return True
        return self.ver_pos == other.ver_pos and self.hor_pos < other.hor_pos

    def neighbour(self, direction: Side):
        if direction.is_vertical:
            return Slot(self.hor_pos - direction.shift_direction, self.ver_pos)
        return Slot(self.hor_pos, self.ver_pos - direction.shift_direction)

    @staticmethod
    def on_edge(side: Side, position: int) -> 'Slot':
        if side.is_vertical:
            return Slot(side.position, position)
        return Slot(position, side.position)


Slot.initialize()


class LineOrientation(Enum):
    HORIZONTAL = 0
    VERTICAL = 1
    DIAGONAL = 2


class Move(namedtuple('Move', 'side position')):

    def __new__(cls, side: Side, position: int):
        if position < 0 or position >= NUM_SLOTS_PER_SIDE:
            raise ValueError("Parameter position has illegal value: {0}".format(position))
        return super().__new__(cls, side, position)

    def __str__(self) -> str:
        return "Move(side = {0}, position = {1})".format(self.side, self.position)


class GameOverCondition:

    def __init__(self, winner: Optional[Colour] = None) -> None:
        self._winner = winner

    def __str__(self) -> str:
        if self._winner is None:
            return "Game over: draw!"
        return "Game over: {0} has won!".format(self._winner)

    @property
    def winner(self) -> Optional[Colour]:
        return self._winner


class InvalidMoveException(Exception):
    pass


class JSONEncoder(json.JSONEncoder):

    KEY_PLAYERS = 'players'
    KEY_BOARD = "board"

    def default(self, o):
        if isinstance(o, Colour):
            return str(o)
        return {JSONEncoder.KEY_PLAYERS: o.players,
                JSONEncoder.KEY_BOARD: [[o.colour_at(Slot(hor_pos, ver_pos)) for hor_pos in range(NUM_SLOTS_PER_SIDE)]
                                        for ver_pos in range(NUM_SLOTS_PER_SIDE)]}


class ShiftagoObserver:

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # forwards all unused arguments

    def notify_marble_shifted(self, slot: Slot, direction: Side):
        pass

    def notify_marble_inserted(self, slot: Slot):
        pass

    def notify_game_over(self):
        pass


class Shiftago(ABC):

    _DEFAULT_OBSERVER = ShiftagoObserver()

    def __init__(self, players: Deque[Colour], board: Optional[Dict[Slot, Colour]] = None) -> None:
        num_players = len(set(players))
        if num_players < len(players):
            raise ValueError("Argument 'players' contains duplicates: {0}".format(players))
        if 2 <= num_players <= len(Colour):
            self._players = players
        else:
            raise ValueError("Illegal number of players!")
        if board is None:
            self._board = {}  # type: Dict[Slot, Colour]
        else:
            self._board = board
        self.observer = self._DEFAULT_OBSERVER

    def __str__(self) -> str:
        string_io = StringIO()
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                colour = self.colour_at(Slot(hor_pos, ver_pos))
                string_io.write('_' if colour is None else str(colour))
                if hor_pos < NUM_SLOTS_PER_SIDE - 1:
                    string_io.write('|')
            if ver_pos < NUM_SLOTS_PER_SIDE - 1:
                string_io.write('\n')
        return string_io.getvalue()

    def serialize(self, output_stream: TextIO):
        json.dump(self, output_stream, indent=4, cls=JSONEncoder)

    @property
    def players(self) -> Tuple[Colour, ...]:
        return tuple(self._players)

    @property
    def current_player(self) -> Colour:
        return self._players[0]

    @property
    def current_opponent(self) -> Colour:
        return self._players[-1]

    @property
    @abstractmethod
    def game_over_condition(self) -> Optional[GameOverCondition]:
        pass

    def colour_at(self, position: Slot) -> Optional[Colour]:
        return self._board.get(position)

    def colour_of_occupied_slot(self, position: Slot) -> Colour:
        c = self._board.get(position)
        if c is None:
            raise ValueError("Slot {0} is not occupied!".format(position))
        return c

    @abstractmethod
    def clone(self) -> 'Shiftago':
        pass

    def __eq__(self, other) -> bool:
        if isinstance(other, Shiftago):
            return (self._players == other._players and self._board == other._board)
        return False

    @abstractmethod
    def apply_move(self, move: Move) -> Optional[GameOverCondition]:
        raise NotImplementedError

    def _insert_marble(self, side: Side, position: int) -> Slot:
        first_empty_slot = self.find_first_empty_slot(side, position)  # type: Optional[Slot]
        if first_empty_slot is None:
            raise InvalidMoveException("No empty slot!")
        if side.is_vertical:
            for hor_pos in range(first_empty_slot.hor_pos, side.position, -side.shift_direction):
                occupied = Slot(hor_pos - side.shift_direction, position)
                self._board[Slot(hor_pos, position)] = self.colour_of_occupied_slot(occupied)
                self.observer.notify_marble_shifted(occupied, side.opposite)
            insert_slot = Slot(side.position, position)
        else:
            for ver_pos in range(first_empty_slot.ver_pos, side.position, -side.shift_direction):
                occupied = Slot(position, ver_pos - side.shift_direction)
                self._board[Slot(position, ver_pos)] = self.colour_of_occupied_slot(occupied)
                self.observer.notify_marble_shifted(occupied, side.opposite)
            insert_slot = Slot(position, side.position)
        self._board[insert_slot] = self._players[0]
        self.observer.notify_marble_inserted(insert_slot)
        return insert_slot

    def find_first_empty_slot(self, side: Side, insert_pos: int) -> Optional[Slot]:
        if side.is_vertical:
            for hor_pos in (range(NUM_SLOTS_PER_SIDE) if side == Side.LEFT else range(NUM_SLOTS_PER_SIDE - 1, -1, -1)):
                position = Slot(hor_pos, insert_pos)
                if self.colour_at(position) is None:
                    return position
        else:
            for ver_pos in (range(NUM_SLOTS_PER_SIDE) if side == Side.TOP else range(NUM_SLOTS_PER_SIDE - 1, -1, -1)):
                position = Slot(insert_pos, ver_pos)
                if self.colour_at(position) is None:
                    return position
        return None

    def count_slots_per_colour(self) -> Dict[Colour, int]:
        slots_per_colour = defaultdict(lambda: 0)
        for c in self._board.values():
            slots_per_colour[c] += 1
        return slots_per_colour

    def count_occupied_slots(self) -> int:
        return len(self._board)

    def detect_all_possible_moves(self) -> List[Move]:
        results = []  # type: List[Move]
        for hor_pos in range(NUM_SLOTS_PER_SIDE):
            if self.find_first_empty_slot(Side.TOP, hor_pos) is not None:
                results.append(Move(Side.TOP, hor_pos))
                results.append(Move(Side.BOTTOM, hor_pos))
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            if self.find_first_empty_slot(Side.LEFT, ver_pos) is not None:
                results.append(Move(Side.LEFT, ver_pos))
                results.append(Move(Side.RIGHT, ver_pos))
        return results

    @staticmethod
    def deserialize_board(board_dict: Dict) -> Dict[Slot, Colour]:
        board = {}  # type: Dict[Slot, Colour]
        for ver_pos, row in enumerate(board_dict):
            for hor_pos, colour_symbol in enumerate(row):
                if colour_symbol is not None:
                    board[Slot(hor_pos, ver_pos)] = Colour(colour_symbol)
        return board

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'Shiftago':
        """Deserializes a JSON input stream to a Board object"""
        def object_hook(json_dict: Dict) -> 'Shiftago':
            return cls(deque(Colour(p) for p in json_dict[JSONEncoder.KEY_PLAYERS]),
                       board=Shiftago.deserialize_board(json_dict[JSONEncoder.KEY_BOARD]))
        return json.load(input_stream, object_hook=object_hook)
