# pylint: disable=consider-using-f-string
from typing import List, Dict, Set, Sequence, Optional, TextIO, Tuple, Type, TypeVar, Generic, Iterator
from abc import ABC, abstractmethod
from enum import Enum
from collections import namedtuple, deque
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
        if self == self.LEFT:
            return self.RIGHT
        if self == self.RIGHT:
            return self.LEFT
        if self == self.TOP:
            return self.BOTTOM
        return self.TOP


@total_ordering
class Slot(namedtuple('Slot', 'hor_pos ver_pos')):

    _instances = [[None for _ in range(NUM_SLOTS_PER_SIDE)]
                  for _ in range(NUM_SLOTS_PER_SIDE)]  # type: List[List[Optional[Slot]]]

    def __new__(cls, hor_pos: int, ver_pos: int) -> 'Slot':
        assert 0 <= ver_pos <= NUM_SLOTS_PER_SIDE, \
            "Parameter ver_pos has illegal value: {0}".format(ver_pos)
        assert 0 <= hor_pos <= NUM_SLOTS_PER_SIDE, \
            "Parameter hor_pos has illegal value: {0}".format(hor_pos)

        slot = cls._instances[ver_pos][hor_pos]

        if slot is None:
            slot = super().__new__(cls, hor_pos, ver_pos)
            cls._instances[ver_pos][hor_pos] = slot
        return slot

    def __str__(self) -> str:
        return "[{0},{1}]".format(self.hor_pos, self.ver_pos)

    def __lt__(self, other) -> bool:
        if self.ver_pos < other.ver_pos:
            return True
        return self.ver_pos == other.ver_pos and self.hor_pos < other.hor_pos

    def neighbour(self, direction: Side) -> 'Slot':
        if direction.is_vertical:
            return Slot(self.hor_pos - direction.shift_direction, self.ver_pos)
        return Slot(self.hor_pos, self.ver_pos - direction.shift_direction)

    @staticmethod
    def on_edge(side: Side, position: int) -> 'Slot':
        if side.is_vertical:
            return Slot(side.position, position)
        return Slot(position, side.position)


class LineOrientation(Enum):

    HORIZONTAL = 0
    VERTICAL = 1
    ASCENDING = 2
    DESCENDING = 3

    def to_neighbour(self, slot: Slot) -> Slot:
        if self == self.HORIZONTAL:
            return Slot(slot.hor_pos + 1, slot.ver_pos)
        if self == self.VERTICAL:
            return Slot(slot.hor_pos, slot.ver_pos + 1)
        if self == self.ASCENDING:
            return Slot(slot.hor_pos + 1, slot.ver_pos - 1)
        return Slot(slot.hor_pos + 1, slot.ver_pos + 1)


class SlotsInLine:

    def __init__(self, orientation: LineOrientation, num_slots: int, start_slot: Slot) -> None:
        self._orientation = orientation

        def generate_line():
            slot = start_slot
            yield slot
            for _ in range(0, num_slots - 1):
                slot = orientation.to_neighbour(slot)
                yield slot
        self._slots = tuple(generate_line())

    def __eq__(self, other) -> bool:
        if isinstance(other, SlotsInLine):
            return self._slots == other._slots
        return False

    def __hash__(self) -> int:
        return hash(self._slots)

    def __str__(self) -> str:
        return ",".join(str(sp) for sp in self._slots)

    @property
    def orientation(self) -> LineOrientation:
        return self._orientation

    @property
    def slots(self) -> Tuple[Slot, ...]:
        return self._slots

    @staticmethod
    def get_all(line_length: int) -> Set['SlotsInLine']:
        all_lines = set()  # type: Set[SlotsInLine]

        def add_all_sub_lines(start_slot: Slot, orientation: LineOrientation, board_line_length: int):
            for _ in range(0, board_line_length - line_length + 1):
                all_lines.add(SlotsInLine(orientation, line_length, start_slot))
                start_slot = orientation.to_neighbour(start_slot)

        for orientation in (LineOrientation.HORIZONTAL, LineOrientation.VERTICAL):
            for offset in range(0, NUM_SLOTS_PER_SIDE):
                add_all_sub_lines(Slot(0, offset) if orientation == LineOrientation.HORIZONTAL else
                                  Slot(offset, 0), orientation, NUM_SLOTS_PER_SIDE)

        for orientation in (LineOrientation.DESCENDING, LineOrientation.ASCENDING):
            max_offset = NUM_SLOTS_PER_SIDE - line_length
            for offset in range(0, max_offset + 1):
                add_all_sub_lines(Slot(0, offset if orientation == LineOrientation.DESCENDING else
                                       NUM_SLOTS_PER_SIDE - 1 - offset), orientation,
                                  NUM_SLOTS_PER_SIDE - offset)
            for offset in range(1, max_offset + 1):
                add_all_sub_lines(Slot(offset, 0 if orientation == LineOrientation.DESCENDING else
                                       NUM_SLOTS_PER_SIDE - 1), orientation,
                                  NUM_SLOTS_PER_SIDE - offset)
        return all_lines


class Move(namedtuple('Move', 'side position')):

    def __new__(cls, side: Side, position: int):
        assert 0 <= position < NUM_SLOTS_PER_SIDE, \
            "Parameter position has illegal value: {0}".format(position)
        return super().__new__(cls, side, position)

    def __str__(self) -> str:
        return "Move(side = {0}, position = {1})".format(self.side, self.position)


class MoveObserver:

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # forwards all unused arguments

    def notify_marble_shifted(self, slot: Slot, direction: Side):
        pass

    def notify_marble_inserted(self, slot: Slot):
        pass


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


class GameOverException(Exception):

    def __init__(self, game_over_condition: GameOverCondition) -> None:
        self._game_over_condition = game_over_condition

    @property
    def game_over_condition(self) -> GameOverCondition:
        return self._game_over_condition


class JSONEncoder(json.JSONEncoder):

    KEY_COLOURS = 'colours'
    KEY_BOARD = "board"

    def default(self, o):
        if isinstance(o, Colour):
            return str(o)
        return {JSONEncoder.KEY_COLOURS: o.colours,
                JSONEncoder.KEY_BOARD: [[o.colour_at(Slot(hor_pos, ver_pos)) for hor_pos in range(NUM_SLOTS_PER_SIDE)]
                                        for ver_pos in range(NUM_SLOTS_PER_SIDE)]}


_S = TypeVar("_S", bound='Shiftago')


class ShiftagoDeser(Generic[_S]):

    def __init__(self, stype: Type[_S]) -> None:
        self._type = stype

    @property
    def type(self) -> Type[_S]:
        return self._type

    def _deserialize_colours(self, json_dict: dict) -> Sequence[Colour]:
        return [Colour(c) for c in json_dict[JSONEncoder.KEY_COLOURS]]

    def _deserialize_board(self, json_dict: Dict) -> Dict[Slot, Colour]:
        board = {}  # type: Dict[Slot, Colour]
        for ver_pos, row in enumerate(json_dict[JSONEncoder.KEY_BOARD]):
            for hor_pos, colour_symbol in enumerate(row):
                if colour_symbol is not None:
                    board[Slot(hor_pos, ver_pos)] = Colour(colour_symbol)
        return board

    def deserialize(self, input_stream: TextIO) -> _S:
        def object_hook(json_dict: Dict) -> 'Shiftago':
            return self._type(colours=self._deserialize_colours(json_dict),
                              board=self._deserialize_board(json_dict))
        return json.load(input_stream, object_hook=object_hook)


class Shiftago(ABC):

    _DEFAULT_MOVE_OBSERVER = MoveObserver()

    @staticmethod
    def _validate_colours(colours: Sequence[Colour]) -> None:
        num_colours = len(set(colours))
        if num_colours < len(colours):
            raise ValueError("Argument 'colours' contains duplicates: {0}".format(colours))
        if not 2 <= num_colours <= len(Colour):
            raise ValueError("Illegal number of colours!")

    def __init__(self, *, orig: Optional['Shiftago'] = None, colours: Optional[Sequence[Colour]] = None,
                 board: Optional[Dict[Slot, Colour]] = None) -> None:
        if orig is not None:
            self._colours = orig._colours.copy()
            self._board = orig._board.copy()
            if colours is not None:
                raise ValueError("Parameters 'orig' and 'colours' exclude each other!")
            if board is not None:
                raise ValueError("Parameters 'orig' and 'board' exclude each other!")
        else:
            if colours is None:
                raise ValueError("Parameters 'colours' is mandatory if 'orig' is None!")
            self._validate_colours(colours)
            self._colours = deque(colours)
            if board is None:
                self._board = {}  # type: Dict[Slot, Colour]
            else:
                self._board = board

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
    def colours(self) -> Sequence[Colour]:
        return self._colours

    @colours.setter
    def colours(self, new_colours: Sequence[Colour]):
        self._set_colours(new_colours)

    def _set_colours(self, colours: Sequence[Colour]) -> None:
        self._validate_colours(colours)
        self._colours = deque(colours)
        self._board.clear()

    @property
    def colour_to_move(self) -> Colour:
        if self.game_over_condition is not None:
            raise GameOverException(self.game_over_condition)
        return self._colours[0]

    @property
    @abstractmethod
    def game_over_condition(self) -> Optional[GameOverCondition]:
        pass

    def slots(self) -> Iterator[Tuple[Slot, Optional[Colour]]]:
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                yield slot, self._board.get(slot)

    def colour_at(self, position: Slot) -> Optional[Colour]:
        return self._board.get(position)

    def colour_of_occupied_slot(self, position: Slot) -> Colour:
        c = self._board.get(position)
        if c is None:
            raise ValueError("Slot {0} is not occupied!".format(position))
        return c

    def __eq__(self, other) -> bool:
        if isinstance(other, Shiftago):
            return (self._colours == other._colours and self._board == other._board)
        return False

    @abstractmethod
    def apply_move(self, move: Move, observer: MoveObserver = _DEFAULT_MOVE_OBSERVER) \
        -> Optional[GameOverCondition]:
        raise NotImplementedError

    def _insert_marble(self, side: Side, position: int, observer: MoveObserver) -> None:
        first_empty_slot = self.find_first_empty_slot(side, position)  # type: Optional[Slot]
        assert first_empty_slot is not None, "No empty slot!"
        if side.is_vertical:
            for hor_pos in range(first_empty_slot.hor_pos, side.position, -side.shift_direction):
                occupied = Slot(hor_pos - side.shift_direction, position)
                self._board[Slot(hor_pos, position)] = self.colour_of_occupied_slot(occupied)
                observer.notify_marble_shifted(occupied, side.opposite)
            insert_slot = Slot(side.position, position)
        else:
            for ver_pos in range(first_empty_slot.ver_pos, side.position, -side.shift_direction):
                occupied = Slot(position, ver_pos - side.shift_direction)
                self._board[Slot(position, ver_pos)] = self.colour_of_occupied_slot(occupied)
                observer.notify_marble_shifted(occupied, side.opposite)
            insert_slot = Slot(position, side.position)
        self._board[insert_slot] = self._colours[0]
        observer.notify_marble_inserted(insert_slot)

    def find_first_empty_slot(self, side: Side, insert_pos: int) -> Optional[Slot]:
        if side.is_vertical:
            for hor_pos in (range(NUM_SLOTS_PER_SIDE) if side == Side.LEFT else
                            range(NUM_SLOTS_PER_SIDE - 1, -1, -1)):
                position = Slot(hor_pos, insert_pos)
                if self.colour_at(position) is None:
                    return position
        else:
            for ver_pos in (range(NUM_SLOTS_PER_SIDE) if side == Side.TOP else
                            range(NUM_SLOTS_PER_SIDE - 1, -1, -1)):
                position = Slot(insert_pos, ver_pos)
                if self.colour_at(position) is None:
                    return position
        return None

    def count_slots_per_colour(self) -> Dict[Colour, int]:
        slots_per_colour = {c: 0 for c in self._colours}
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

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'Shiftago':
        """Deserializes a JSON input stream to a Shiftago instance"""
        return ShiftagoDeser(cls).deserialize(input_stream)


class SkillLevel(Enum):

    ROOKIE = 0
    ADVANCED = 1
    EXPERT = 2
    GRANDMASTER = 3


class AIEngine(ABC, Generic[_S]):

    def __init__(self, skill_level: SkillLevel) -> None:
        self._skill_level = skill_level

    @property
    def skill_level(self) -> SkillLevel:
        return self._skill_level

    @abstractmethod
    def select_move(self, game_state: _S) -> Move:
        raise NotImplementedError
