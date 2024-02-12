# pylint: disable=consider-using-f-string
from typing import Tuple, Dict, Set, Sequence, Optional, TextIO
from collections import defaultdict
from shiftago.core import NUM_MARBLES_PER_COLOUR, NUM_SLOTS_PER_SIDE
from shiftago.core import ShiftagoDeser, Slot, Colour, LineOrientation, Shiftago, Move, \
    GameOverCondition, GameOverException


class WinningLine:

    @staticmethod
    def _to_neighbour(slot: Slot, orientation: LineOrientation) -> Slot:
        if orientation == LineOrientation.HORIZONTAL:
            return Slot(slot.hor_pos + 1, slot.ver_pos)
        if orientation == LineOrientation.VERTICAL:
            return Slot(slot.hor_pos, slot.ver_pos + 1)
        if orientation == LineOrientation.ASCENDING:
            return Slot(slot.hor_pos + 1, slot.ver_pos - 1)
        return Slot(slot.hor_pos + 1, slot.ver_pos + 1)

    def __init__(self, orientation: LineOrientation, num_slots: int, start_slot: Slot) -> None:
        self._orientation = orientation

        def generate_line():
            slot = start_slot
            yield slot
            for _ in range(0, num_slots - 1):
                slot = self._to_neighbour(slot, orientation)
                yield slot
        self._slots = tuple(generate_line())

    def __eq__(self, other) -> bool:
        if isinstance(other, WinningLine):
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
    def get_all(num_slots_in_line: int) -> Set['WinningLine']:
        all_winning_lines = set()  # type: Set[WinningLine]

        def add_all_sub_lines(start_slot: Slot, orientation: LineOrientation, board_line_length: int):
            for _ in range(0, board_line_length - num_slots_in_line + 1):
                all_winning_lines.add(WinningLine(orientation, num_slots_in_line, start_slot))
                start_slot = WinningLine._to_neighbour(start_slot, orientation)

        for orientation in (LineOrientation.HORIZONTAL, LineOrientation.VERTICAL):
            for offset in range(0, NUM_SLOTS_PER_SIDE):
                add_all_sub_lines(Slot(0, offset) if orientation == LineOrientation.HORIZONTAL else
                                  Slot(offset, 0), orientation, NUM_SLOTS_PER_SIDE)

        for orientation in (LineOrientation.DESCENDING, LineOrientation.ASCENDING):
            max_offset = NUM_SLOTS_PER_SIDE - num_slots_in_line
            for offset in range(0, max_offset + 1):
                add_all_sub_lines(Slot(0, offset if orientation == LineOrientation.DESCENDING else
                                       NUM_SLOTS_PER_SIDE - 1 - offset), orientation,
                                  NUM_SLOTS_PER_SIDE - offset)
            for offset in range(1, max_offset + 1):
                add_all_sub_lines(Slot(offset, 0 if orientation == LineOrientation.DESCENDING else
                                       NUM_SLOTS_PER_SIDE - 1), orientation,
                                  NUM_SLOTS_PER_SIDE - offset)
        return all_winning_lines


class WinningLinesDetector:

    def __init__(self, winning_line_length: int) -> None:
        if not 4 <= winning_line_length <= 5:
            raise ValueError("Illegal winning line length: {0}".format(winning_line_length))
        self._winning_line_length = winning_line_length
        self._slot_to_lines = defaultdict(set)  # type: Dict[Slot, Set[WinningLine]]
        for wl in WinningLine.get_all(winning_line_length):
            for slot in wl.slots:
                self._slot_to_lines[slot].add(wl)

    @property
    def winning_line_length(self) -> int:
        return self._winning_line_length

    def detect_winning_lines(self, shiftago: Shiftago, min_match_count: Optional[int] = None) \
            -> Sequence[Dict[WinningLine, int]]:
        if min_match_count is None:
            min_match_count = self._winning_line_length
        colour_indexes = {colour: index for index, colour in enumerate(shiftago.colours)}
        wl_matches_per_colour = [defaultdict(lambda: 0) for _ in shiftago.colours]
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                c = shiftago.colour_at(slot)
                if c is not None:
                    wl_match_dict = wl_matches_per_colour[colour_indexes[c]]
                    for wl in self._slot_to_lines[slot]:
                        wl_match_dict[wl] += 1
        return tuple({wl: match_count for wl, match_count in wl_match_dict.items()
                      if match_count >= min_match_count} for wl_match_dict in wl_matches_per_colour)

    def has_winning_line(self, shiftago: Shiftago, colour: Colour) -> bool:
        wl_match_dict = defaultdict(lambda: 0)  # type: Dict[WinningLine, int]
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                if shiftago.colour_at(slot) == colour:
                    for wl in self._slot_to_lines[slot]:
                        wl_match_dict[wl] += 1
        for match_count in wl_match_dict.values():
            if match_count == self._winning_line_length:
                return True
        return False


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
        return self._winning_lines_detector.winning_line_length

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

    def detect_winning_lines(self, min_match_count: Optional[int] = None) -> Sequence[Dict[WinningLine, int]]:
        return self._winning_lines_detector.detect_winning_lines(self, min_match_count)

    def _select_colour_to_move(self) -> Colour:
        self._colours.rotate(-1)
        return self._colours[0]

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'ShiftagoExpress':
        """Deserializes a JSON input stream to a ShiftagoExpress instance"""
        return ShiftagoDeser(cls).deserialize(input_stream)
