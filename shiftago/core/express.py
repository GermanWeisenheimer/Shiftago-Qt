# pylint: disable=consider-using-f-string
from typing import Dict, Set, Sequence, Optional, TextIO
from collections import defaultdict
from shiftago.core import NUM_MARBLES_PER_COLOUR, NUM_SLOTS_PER_SIDE
from shiftago.core import ShiftagoDeser, Slot, Colour, SlotsInLine, Shiftago, Move, \
    MoveObserver, GameOverCondition


class WinningLinesDetector:
    """
    WinningLinesDetector is responsible for detecting potential winning lines on the game board.
    It initializes with a specified winning match degree, which determines the length of the 
    line required to win the game. The class provides methods to analyze the game board and 
    determine the match degrees for each line.

    Attributes:
    _winning_match_degree (int): The length of the line required to win the game.
    _slot_to_lines (Dict[Slot, Set[SlotsInLine]]): A mapping from each slot to the set of 
    potential winning lines that include that slot.
    """

    def __init__(self, winning_match_degree: int) -> None:
        if not 4 <= winning_match_degree <= 5:
            raise ValueError("Illegal winning line length: {0}".format(winning_match_degree))
        self._winning_match_degree = winning_match_degree
        self._slot_to_lines = defaultdict(set)  # type: Dict[Slot, Set[SlotsInLine]]
        for line in SlotsInLine.get_all(winning_match_degree):
            for slot in line.slots:
                self._slot_to_lines[slot].add(line)

    @property
    def winning_match_degree(self) -> int:
        return self._winning_match_degree

    def determine_match_degrees(self, shiftago: Shiftago, min_match_degree: Optional[int] = None) \
            -> Sequence[Dict[SlotsInLine, int]]:
        """
        Determines the match degrees for each line on the game board for each colour. The match degree 
        is the number of consecutive slots occupied by the same colour in a potential winning line.

        Parameters:
        shiftago (Shiftago): The current state of the game.
        min_match_degree (Optional[int]): The minimum match degree to consider. If not provided, 
                                          it defaults to the winning match degree.

        Returns:
        Sequence[Dict[SlotsInLine, int]]: A sequence of dictionaries where each dictionary corresponds 
                                          to a colour and maps each potential winning line to its match degree.
        """
        if min_match_degree is None:
            min_match_degree = self._winning_match_degree
        match_degrees_per_colour = {colour: defaultdict(lambda: 0) for colour in
                                    shiftago.colours}  # type: Dict[Colour, Dict[SlotsInLine, int]]
        for slot, colour in shiftago.slots():
            if colour is not None:
                match_degrees = match_degrees_per_colour[colour]
                for line in self._slot_to_lines[slot]:
                    match_degrees[line] += 1
        return tuple({line: match_degree for line, match_degree in match_degrees_per_colour[colour].items()
                      if match_degree >= min_match_degree} for colour in shiftago.colours)

    def has_winning_line(self, shiftago: Shiftago, colour: Colour) -> bool:
        """
        Checks if the specified colour has a winning line on the game board. A winning line is 
        a line where the number of consecutive slots occupied by the same colour equals the 
        winning match degree.

        Parameters:
        shiftago (Shiftago): The current state of the game.
        colour (Colour): The colour to check for a winning line.

        Returns:
        bool: True if the specified colour has a winning line, False otherwise.
        """
        for match_degree in self._build_match_degrees(shiftago, colour).values():
            if match_degree == self._winning_match_degree:
                return True
        return False

    def winning_lines_of(self, shiftago: Shiftago, colour: Colour) -> Set[SlotsInLine]:
        """
        Determines the set of winning lines for the specified colour on the game board. A winning line 
        is a line where the number of consecutive slots occupied by the same colour equals the winning 
        match degree.

        Parameters:
        shiftago (Shiftago): The current state of the game.
        colour (Colour): The colour to check for winning lines.

        Returns:
        Set[SlotsInLine]: A set of winning lines for the specified colour.
        """
        match_degrees = self._build_match_degrees(shiftago, colour)
        return set(filter(lambda line: match_degrees[line] == self._winning_match_degree,
                          match_degrees.keys()))

    def _build_match_degrees(self, shiftago: Shiftago, colour: Colour) -> Dict[SlotsInLine, int]:
        match_degrees = defaultdict(lambda: 0)  # type: Dict[SlotsInLine, int]
        for slot, slot_col in shiftago.slots():
            if slot_col == colour:
                for line in self._slot_to_lines[slot]:
                    match_degrees[line] += 1
        return match_degrees


class ShiftagoExpress(Shiftago):
    """
    ShiftagoExpress is a subclass of Shiftago that implements the 'express' variant of the game.
    This variant uses different winning line detectors based on the number of colours in the game.
    """

    _WINNING_LINES_DETECTOR_4 = WinningLinesDetector(4)
    _WINNING_LINES_DETECTOR_5 = WinningLinesDetector(5)

    @staticmethod
    def _select_winning_lines_detector(colours: Sequence[Colour]) -> WinningLinesDetector:
        if 3 <= len(colours) <= 4:
            return ShiftagoExpress._WINNING_LINES_DETECTOR_4
        return ShiftagoExpress._WINNING_LINES_DETECTOR_5

    def __init__(self, *, orig: Optional['ShiftagoExpress'] = None, colours: Optional[Sequence[Colour]] = None,
                 board: Optional[Dict[Slot, Colour]] = None) -> None:
        """
        Initializes a new instance of the ShiftagoExpress class.

        Parameters:
        orig (Optional[ShiftagoExpress]): An optional original ShiftagoExpress instance to copy from.
        colours (Optional[Sequence[Colour]]): An optional sequence of colours for the game.
        board (Optional[Dict[Slot, Colour]]): An optional dictionary representing the game board state.

        Raises:
        ValueError: If 'colours' is not provided when 'orig' is None.
        """
        super().__init__(orig=orig, colours=colours, board=board)
        if orig is not None:
            self._game_over_condition = orig._game_over_condition
            self._winning_lines_detector = orig._winning_lines_detector
        else:
            if colours is None:
                raise ValueError("Parameters 'colours' is mandatory if 'orig' is None!")
            self._winning_lines_detector = self._select_winning_lines_detector(colours)
            self._game_over_condition = None

    @Shiftago.colours.setter
    def colours(self, new_colours: Sequence[Colour]):
        """
        Sets the colours for the game and updates the winning lines detector and game over condition.

        Parameters:
        new_colours (Sequence[Colour]): The new colours to be set.
        """
        super()._set_colours(new_colours)
        self._winning_lines_detector = self._select_winning_lines_detector(new_colours)
        self._game_over_condition = None

    @property
    def winning_line_length(self) -> int:
        """
        Returns the length of the winning line required to win the game.

        Returns:
        int: The length of the winning line.
        """
        return self._winning_lines_detector.winning_match_degree

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        """
        Returns the condition of the game when it is over.

        Returns:
        Optional[GameOverCondition]: The condition of the game when it is over, or None if the game is not over.
        """
        return self._game_over_condition

    def __copy__(self) -> 'ShiftagoExpress':
        """
        Creates a copy of the current game state.

        Returns:
        ShiftagoExpress: A copy of the current game state.
        """
        return ShiftagoExpress(orig=self)

    def apply_move(self, move: Move, observer: MoveObserver = Shiftago._DEFAULT_MOVE_OBSERVER) \
            -> Optional[GameOverCondition]:
        """
        Applies the given move to the game board and updates the game state accordingly.

        Parameters:
        move (Move): The move to be applied.
        observer (MoveObserver): An observer to be notified of move events (default is Shiftago._DEFAULT_MOVE_OBSERVER).

        Returns:
        Optional[GameOverCondition]: The condition of the game after the move is applied,
        or None if the game is not over.

        Raises:
        AssertionError: If the game is already over.
        """
        assert self._game_over_condition is None, "Game is already over!"

        colour_to_move = self.colour_to_move
        self._insert_marble(move.side, move.position, observer)

        # check if the match has been won by the move
        if self._winning_lines_detector.has_winning_line(self, colour_to_move):
            self._game_over_condition = GameOverCondition(colour_to_move)
        else:
            num_slots_per_colour = self.count_slots_per_colour()
            # check if there is a free slot left
            if sum(num_slots_per_colour.values()) < NUM_SLOTS_PER_SIDE * NUM_SLOTS_PER_SIDE:
                # check if the colour to move next has one available marble at least
                if num_slots_per_colour[self._colours[1]] == NUM_MARBLES_PER_COLOUR:
                    self._game_over_condition = GameOverCondition()
                else:
                    self._colours.rotate(-1)  # switch colour to move
            else:
                # all slots are occupied
                self._game_over_condition = GameOverCondition()
        return self._game_over_condition

    def detect_winning_lines(self, min_match_count: Optional[int] = None) -> Sequence[Dict[SlotsInLine, int]]:
        """
        Detects all potential winning lines on the game board and their match degrees for each colour.

        Parameters:
        min_match_count (Optional[int]): The minimum match degree to consider. If not provided, 
                                         it defaults to the winning match degree.

        Returns:
        Sequence[Dict[SlotsInLine, int]]: A sequence of dictionaries where each dictionary corresponds 
                                          to a colour and maps each potential winning line to its match degree.
        """
        return self._winning_lines_detector.determine_match_degrees(self, min_match_count)

    def winning_lines_of_winner(self) -> Set[SlotsInLine]:
        """
        Determines the set of winning lines for the winning colour on the game board.

        Returns:
        Set[SlotsInLine]: A set of winning lines for the winning colour.

        Raises:
        AssertionError: If the game is not over or there is no winner.
        """
        assert self._game_over_condition is not None and self._game_over_condition.winner is not None
        return self._winning_lines_detector.winning_lines_of(self, self._game_over_condition.winner)

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'ShiftagoExpress':
        """
        Deserializes a JSON input stream to a ShiftagoExpress instance.

        Parameters:
        input_stream (TextIO): The input stream containing the JSON representation of the game state.

        Returns:
        ShiftagoExpress: An instance of ShiftagoExpress deserialized from the input stream.
        """
        return ShiftagoDeser(cls).deserialize(input_stream)
