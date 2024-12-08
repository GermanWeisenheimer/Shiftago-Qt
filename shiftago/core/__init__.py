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
    """
    Colour is an enumeration representing the different colours of marbles used in the game.

    Attributes:
    BLUE: Represents the blue colour marble.
    GREEN: Represents the green colour marble.
    ORANGE: Represents the orange colour marble.
    """

    BLUE = 'B'
    GREEN = 'G'
    ORANGE = 'O'

    def __str__(self) -> str:
        return self.value


class Side(Enum):
    """
    Side is an enumeration representing the four sides of the game board. Each side has 
    specific attributes that define its position and behavior in the game.

    Attributes:
    LEFT (tuple): Represents the left side of the board with its specific attributes.
    RIGHT (tuple): Represents the right side of the board with its specific attributes.
    TOP (tuple): Represents the top side of the board with its specific attributes.
    BOTTOM (tuple): Represents the bottom side of the board with its specific attributes.
    """

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
        """
        Returns the position of the side on the game board.
        """
        return self._position

    @property
    def is_horizontal(self) -> bool:
        """
        Returns whether the side is horizontal.

        Returns:
        True if the side is horizontal, False otherwise.
        """
        return self._is_horizontal

    @property
    def is_vertical(self) -> bool:
        """
        Returns whether the side is vertical.

        Returns:
        True if the side is vertical, False otherwise.
        """
        return not self._is_horizontal

    @property
    def shift_direction(self) -> int:
        """
        Returns the shift direction of the side.
        """
        return self._shift_direction

    @property
    def opposite(self) -> 'Side':
        """
        Returns the opposite side of the current side of the game board.

        Returns:
        The opposite side of the current side (LEFT <-> RIGHT, TOP <-> BOTTOM).
        """
        if self == self.LEFT:
            return self.RIGHT
        if self == self.RIGHT:
            return self.LEFT
        if self == self.TOP:
            return self.BOTTOM
        return self.TOP


@total_ordering
class Slot(namedtuple('Slot', 'hor_pos ver_pos')):
    """
    Slot represents a position on the game board with horizontal and vertical coordinates.
    It uses the total_ordering decorator to provide comparison methods based on the 
    coordinates, allowing slots to be compared and sorted.

    Attributes:
    hor_pos (int): The horizontal position of the slot.
    ver_pos (int): The vertical position of the slot.
    """

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
        """
        Returns the neighbouring Slot in the specified direction.
        """
        if direction.is_vertical:
            return Slot(self.hor_pos - direction.shift_direction, self.ver_pos)
        return Slot(self.hor_pos, self.ver_pos - direction.shift_direction)

    @staticmethod
    def on_edge(side: Side, position: int) -> 'Slot':
        """
        Returns a Slot representing a position on the edge of the game board.

        Parameters:
        side: The side of the game board where the slot is located.
        position: The position along the specified side.
        """
        if side.is_vertical:
            return Slot(side.position, position)
        return Slot(position, side.position)


class LineOrientation(Enum):
    """
    LineOrientation is an enumeration representing the possible orientations of lines on the game board.
    It defines four orientations: HORIZONTAL, VERTICAL, ASCENDING, and DESCENDING.

    Attributes:
    HORIZONTAL: Represents a horizontal line orientation.
    VERTICAL: Represents a vertical line orientation.
    ASCENDING: Represents an ascending diagonal line orientation.
    DESCENDING: Represents a descending diagonal line orientation.
    """

    HORIZONTAL = 0
    VERTICAL = 1
    ASCENDING = 2
    DESCENDING = 3

    def to_neighbour(self, slot: Slot) -> Slot:
        """
        Returns the neighbouring Slot object in the direction of the line orientation.
        """
        if self == self.HORIZONTAL:
            return Slot(slot.hor_pos + 1, slot.ver_pos)
        if self == self.VERTICAL:
            return Slot(slot.hor_pos, slot.ver_pos + 1)
        if self == self.ASCENDING:
            return Slot(slot.hor_pos + 1, slot.ver_pos - 1)
        return Slot(slot.hor_pos + 1, slot.ver_pos + 1)


class SlotsInLine:
    """
    SlotsInLine represents a sequence of slots on the game board that form a line with a specific orientation.
    It is used to identify and work with potential winning lines in the game.
    """

    def __init__(self, orientation: LineOrientation, num_slots: int, start_slot: Slot) -> None:
        """
        Initializes a SlotsInLine instance with the given orientation, number of slots
        and starting slot.
        """
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
        """
        Returns the orientation of the line.
        """
        return self._orientation

    @property
    def slots(self) -> Tuple[Slot, ...]:
        """
        Returns the slots that form the line.
        """
        return self._slots

    @staticmethod
    def get_all(line_length: int) -> Set['SlotsInLine']:
        """
        Generates all possible lines of a given length (winning match degree) on the game board.
        This method creates lines in all orientations (HORIZONTAL, VERTICAL, ASCENDING, DESCENDING)
        starting from every possible slot on the board.
        """
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
    """
    Move represents a move in the game, defined by the side of the board from which the move is made 
    and the position along that side. It is used to encapsulate the details of a move.

    Attributes:
    side (Side): The side of the board from which the move is made.
    position (int): The position along the specified side where the move is made.
    """

    def __new__(cls, side: Side, position: int):
        assert 0 <= position < NUM_SLOTS_PER_SIDE, \
            "Parameter position has illegal value: {0}".format(position)
        return super().__new__(cls, side, position)

    def __str__(self) -> str:
        return "Move(side = {0}, position = {1})".format(self.side, self.position)


class MoveObserver:
    """
    MoveObserver is an observer class that provides methods to be notified of changes in the game state.
    It is used to observe and react to specific events such as marble shifts and insertions.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)  # forwards all unused arguments

    def notify_marble_shifted(self, slot: Slot, direction: Side):
        """
        Notifies that a marble has been shifted in the specified direction.

        Parameters:
        slot: The slot from which the marble was shifted.
        direction: The direction in which the marble was shifted.
        """

    def notify_marble_inserted(self, slot: Slot):
        """
        Notifies that a marble has been inserted into the specified slot.
        """


class GameOverCondition:
    """
    GameOverCondition represents the condition of the game when it is over. It
    indicates whether there is a winner or if the game ended in a draw.
    """

    def __init__(self, winner: Optional[Colour] = None) -> None:
        """
        Initializes a GameOverCondition instance with an optional winner (winning colour).
        If the game ended in a draw, the winner is None.
        """
        self._winner = winner

    def __str__(self) -> str:
        if self._winner is None:
            return "Game over: draw!"
        return "Game over: {0} has won!".format(self._winner)

    @property
    def winner(self) -> Optional[Colour]:
        """
        Returns the colour of the winning player, or None if the game ended in a draw.
        """
        return self._winner


class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder is a custom JSON encoder for serializing the game state of a Shiftago game.
    It provides methods to convert Colour objects and the game board state into a JSON-compatible format.

    Attributes:
    KEY_COLOURS: The key used to store the colours in the JSON representation.
    KEY_BOARD: The key used to store the board state in the JSON representation.
    """

    KEY_COLOURS = 'colours'
    KEY_BOARD = 'board'

    def default(self, o):
        if isinstance(o, Colour):
            return str(o)
        return {JSONEncoder.KEY_COLOURS: o.colours,
                JSONEncoder.KEY_BOARD: [[o.colour_at(Slot(hor_pos, ver_pos)) for hor_pos in range(NUM_SLOTS_PER_SIDE)]
                                        for ver_pos in range(NUM_SLOTS_PER_SIDE)]}


ShiftagoT = TypeVar('ShiftagoT', bound='Shiftago')
"""
ShiftagoT is a type variable that is bound to the Shiftago class.
It is used to specify the type of Shiftago game being deserialized.
"""


class ShiftagoDeser(Generic[ShiftagoT]):
    """
    ShiftagoDeser is a generic class responsible for deserializing the game state of a Shiftago game 
    from a JSON representation. It provides methods to deserialize the colours and the board state.
    """

    def __init__(self, stype: Type[ShiftagoT]) -> None:
        self._type = stype

    @property
    def type(self) -> Type[ShiftagoT]:
        """
        Returns the type of the Shiftago game to be deserialized.
        """
        return self._type

    def _deserialize_colours(self, json_dict: dict) -> Sequence[Colour]:
        """
        Deserializes the colours from the JSON dictionary.
        """
        return [Colour(c) for c in json_dict[JSONEncoder.KEY_COLOURS]]

    def _deserialize_board(self, json_dict: Dict) -> Dict[Slot, Colour]:
        """
        Deserializes the board state from the JSON dictionary.
        """
        board = {}  # type: Dict[Slot, Colour]
        for ver_pos, row in enumerate(json_dict[JSONEncoder.KEY_BOARD]):
            for hor_pos, colour_symbol in enumerate(row):
                if colour_symbol is not None:
                    board[Slot(hor_pos, ver_pos)] = Colour(colour_symbol)
        return board

    def deserialize(self, input_stream: TextIO) -> ShiftagoT:
        """
        Deserializes the Shiftago game state from an input stream.

        Returns:
        An instance of the Shiftago game deserialized from the input stream.
        """
        def object_hook(json_dict: Dict) -> ShiftagoT:
            return self._type(colours=self._deserialize_colours(json_dict),
                              board=self._deserialize_board(json_dict))
        return json.load(input_stream, object_hook=object_hook)


class Shiftago(ABC):
    """
    Shiftago is an abstract base class representing the core game logic for the Shiftago game.
    It provides methods and attributes to manage the game state, validate moves, and handle 
    game-specific operations.
    """

    _DEFAULT_MOVE_OBSERVER = MoveObserver()

    @staticmethod
    def _validate_colours(colours: Sequence[Colour]) -> None:
        """
        Validates the list of colours to ensure there are no duplicates and the number of colours 
        is within the allowed range. If the validation fails, it raises a ValueError.
        """
        num_colours = len(set(colours))
        if num_colours < len(colours):
            raise ValueError("Argument 'colours' contains duplicates: {0}".format(colours))
        if not 2 <= num_colours <= len(Colour):
            raise ValueError("Illegal number of colours!")

    def __init__(self, *, orig: Optional['Shiftago'] = None, colours: Optional[Sequence[Colour]] = None,
                 board: Optional[Dict[Slot, Colour]] = None) -> None:
        """
        Initializes a new instance of the Shiftago class.

        Parameters:
        orig: An optional original Shiftago instance to copy from.
        colours: An optional sequence of colours for the game.
        board: An optional dictionary representing the game board state.

        Raises:
        ValueError: If 'colours' is not provided when 'orig' is None.
        """
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
        """
        Serializes the current game state to a JSON output stream.
        """
        json.dump(self, output_stream, indent=4, cls=JSONEncoder)

    @property
    def colours(self) -> Sequence[Colour]:
        """
        Returns the sequence of colours used in the game. The first element of the
        sequence identifies the current player.
        """
        return self._colours

    @colours.setter
    def colours(self, new_colours: Sequence[Colour]):
        """
        Sets the colours for the game and updates the winning lines detector and game over condition.
        """
        self._set_colours(new_colours)

    def _set_colours(self, colours: Sequence[Colour]) -> None:
        self._validate_colours(colours)
        self._colours = deque(colours)
        self._board.clear()

    @property
    def colour_to_move(self) -> Colour:
        """
        Returns the colour of the player whose turn it is to move.
        If the game is already over, it raises an AssertionError.
        """
        assert self.game_over_condition is None, "Game is already over!"
        return self._colours[0]

    @property
    @abstractmethod
    def game_over_condition(self) -> Optional[GameOverCondition]:
        """
        Abstract property that returns the condition of the game when it is over.
        If the game is not over, it returns None.

        This property should be implemented by subclasses to provide the specific game over condition.
        """

    def slots(self) -> Iterator[Tuple[Slot, Optional[Colour]]]:
        """
        Yields all slots on the game board along with their corresponding colours, if occupied.
        """
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                yield slot, self._board.get(slot)

    def colour_at(self, position: Slot) -> Optional[Colour]:
        """
        Returns the colour of the marble at the specified slot position on the game board.
        If the slot is unoccupied, it returns None.
        """
        return self._board.get(position)

    def colour_of_occupied_slot(self, position: Slot) -> Colour:
        """
        Returns the colour of the marble at the specified slot position on the game board.
        If the slot is not occupied, it raises a ValueError.
        """
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
        """
        Applies the given move to the game board and updates the game state accordingly.
        This method must be implemented by subclasses to define the specific behavior of applying a move.

        Parameters:
        move: The move to be applied.
        observer: An observer to be notified of move events (default is _DEFAULT_MOVE_OBSERVER).

        Returns:
        The condition of the game after the move is applied, or None if the game is not over.
        """

    def _insert_marble(self, side: Side, position: int, observer: MoveObserver) -> None:
        """
        Inserts a marble into the game board from the specified side and position, shifting other marbles as necessary.
        Notifies the observer of marble shifts and insertions.

        Parameters:
        side: The side of the board from which the marble is inserted.
        position: The position along the specified side where the marble is inserted.
        observer: An observer to be notified of marble shift and insertion events.
        """
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
        """
        Finds the first empty slot in the specified column or row where a marble can be inserted.
        If no empty slot is available, it returns None.
        Parameters:
        side: The side of the board from which the marble is to be inserted.
        insert_pos: The position along the specified side to check for the first empty slot.

        Returns:
        The first empty Slot object if found, else None.
        """
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
        """
        Counts the number of slots occupied by each colour on the game board.
        """
        slots_per_colour = {c: 0 for c in self._colours}
        for c in self._board.values():
            slots_per_colour[c] += 1
        return slots_per_colour

    def count_occupied_slots(self) -> int:
        """
        Counts the number of occupied slots on the game board.
        """
        return len(self._board)

    def detect_all_possible_moves(self) -> List[Move]:
        """
        Detects all possible moves that can be made on the game board. A move is possible
        if there is at least one empty slot in the corresponding row or column.
        """
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


class SkillLevel(Enum):
    """
    SkillLevel is an enumeration representing the different skill levels for the AI in the game.
    It defines four levels of difficulty: ROOKIE, ADVANCED, EXPERT, and GRANDMASTER.

    Attributes:
    ROOKIE: Represents the rookie skill level, suitable for beginners.
    ADVANCED: Represents the advanced skill level, suitable for intermediate players.
    EXPERT: Represents the expert skill level, suitable for experienced players.
    GRANDMASTER: Represents the grandmaster skill level, suitable for highly skilled players.
    """

    ROOKIE = 0
    ADVANCED = 1
    EXPERT = 2
    GRANDMASTER = 3


class AIEngine(ABC, Generic[ShiftagoT]):
    """
    AIEngine is an abstract base class representing the AI engine for the game. It defines the 
    interface and common functionality for AI implementations at different skill levels.
    """

    def __init__(self, skill_level: SkillLevel) -> None:
        """
        Initializes the AIEngine with the given skill level.
        """
        self._skill_level = skill_level

    @property
    def skill_level(self) -> SkillLevel:
        """
        Returns the skill level of the AI.
        """
        return self._skill_level

    @abstractmethod
    def select_move(self, game_state: ShiftagoT) -> Move:
        """
        Selects the best move for the AI based on the current game state.

        Parameters:
        game_state: The current state of the game.

        Returns:
        The selected move.
        """
