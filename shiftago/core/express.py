# pylint: disable=consider-using-f-string
from typing import Dict, Set, Sequence, Optional, TextIO
from collections import defaultdict
from shiftago.core import NUM_MARBLES_PER_COLOUR, NUM_SLOTS_PER_SIDE
from shiftago.core import ShiftagoDeser, Slot, Colour, SlotsInLine, Shiftago, Move, \
    GameOverCondition, GameOverException


class WinningLinesDetector:

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
        if min_match_degree is None:
            min_match_degree = self._winning_match_degree
        match_degrees_per_colour = {colour: defaultdict(lambda: 0) for colour in \
                                    shiftago.colours}  # type: Dict[Colour, Dict[SlotsInLine, int]]
        for slot, colour in shiftago.slots():
            if colour is not None:
                match_degrees = match_degrees_per_colour[colour]
                for line in self._slot_to_lines[slot]:
                    match_degrees[line] += 1
        return tuple({line: match_degree for line, match_degree in match_degrees_per_colour[colour].items()
                      if match_degree >= min_match_degree} for colour in shiftago.colours)

    def has_winning_line(self, shiftago: Shiftago, colour: Colour) -> bool:
        for match_degree in self._build_match_degrees(shiftago, colour).values():
            if match_degree == self._winning_match_degree:
                return True
        return False

    def winning_lines_of(self, shiftago: Shiftago, colour: Colour) -> Set[SlotsInLine]:
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

    _WINNING_LINES_DETECTOR_4 = WinningLinesDetector(4)
    _WINNING_LINES_DETECTOR_5 = WinningLinesDetector(5)

    @staticmethod
    def _select_winning_lines_detector(colours: Sequence[Colour]) -> WinningLinesDetector:
        if 3 <= len(colours) <= 4:
            return ShiftagoExpress._WINNING_LINES_DETECTOR_4
        return ShiftagoExpress._WINNING_LINES_DETECTOR_5

    def __init__(self, *, orig: Optional['ShiftagoExpress'] = None, colours: Optional[Sequence[Colour]] = None,
                 board: Optional[Dict[Slot, Colour]] = None) -> None:
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
        super()._set_colours(new_colours)
        self._winning_lines_detector = self._select_winning_lines_detector(new_colours)
        self._game_over_condition = None

    @property
    def winning_line_length(self) -> int:
        return self._winning_lines_detector.winning_match_degree

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._game_over_condition

    def __copy__(self) -> 'ShiftagoExpress':
        return ShiftagoExpress(orig=self)

    def apply_move(self, move: Move) -> Optional[GameOverCondition]:
        if self._game_over_condition is not None:
            raise GameOverException(self._game_over_condition)

        colour_to_move = self.colour_to_move
        self._insert_marble(move.side, move.position)

        # check if the match has been won by the move
        if self._winning_lines_detector.has_winning_line(self, colour_to_move):
            self._game_over_condition = GameOverCondition(colour_to_move)
        else:
            num_slots_per_colour = self.count_slots_per_colour()
            # check if there is a free slot left
            if sum(num_slots_per_colour.values()) < NUM_SLOTS_PER_SIDE * NUM_SLOTS_PER_SIDE:
                next_colour_to_move = self._select_colour_to_move()
                # check if selected colour has one available marble at least
                if num_slots_per_colour[next_colour_to_move] == NUM_MARBLES_PER_COLOUR:
                    self._game_over_condition = GameOverCondition()
            else:
                # all slots are occupied
                self._game_over_condition = GameOverCondition()
        if self._game_over_condition is not None:
            self.observer.notify_game_over()
        return self._game_over_condition

    def detect_winning_lines(self, min_match_count: Optional[int] = None) -> Sequence[Dict[SlotsInLine, int]]:
        return self._winning_lines_detector.determine_match_degrees(self, min_match_count)

    def winning_lines_of_winner(self) -> Set[SlotsInLine]:
        assert self._game_over_condition is not None and self._game_over_condition.winner is not None
        return self._winning_lines_detector.winning_lines_of(self, self._game_over_condition.winner)

    def _select_colour_to_move(self) -> Colour:
        self._colours.rotate(-1)
        return self._colours[0]

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'ShiftagoExpress':
        """Deserializes a JSON input stream to a ShiftagoExpress instance"""
        return ShiftagoDeser(cls).deserialize(input_stream)
