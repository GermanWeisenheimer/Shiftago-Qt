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
        slots = [start_slot]
        slot = start_slot
        for _ in range(0, num_slots - 1):
            slot = self._to_neighbour(slot, orientation)
            slots.append(slot)
        self._slots = tuple(slots)

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
        self._slot_to_lines = defaultdict(set)
        for wl in WinningLine.get_all(winning_line_length):
            for slot in wl.slots:
                self._slot_to_lines[slot].add(wl)

    @property
    def winning_line_length(self) -> int:
        return self._winning_line_length

    def winning_lines_at(self, slot: Slot) -> Set[WinningLine]:
        return self._slot_to_lines[slot]

    def detect_winning_lines(self, shiftago: Shiftago, min_match_count: Optional[int] = None) \
            -> Sequence[Dict[WinningLine, int]]:
        if min_match_count is None:
            min_match_count = self._winning_line_length
        player_indexes = {player: index for index, player in enumerate(shiftago.players)}
        wl_matches_per_player = [defaultdict(lambda: 0) for _ in shiftago.players]
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                c = shiftago.colour_at(slot)
                if c is not None:
                    wl_match_dict = wl_matches_per_player[player_indexes[c]]
                    for wl in self._slot_to_lines[slot]:
                        wl_match_dict[wl] += 1
        return tuple({wl: match_count for wl, match_count in wl_match_dict.items()
                      if match_count >= min_match_count} for wl_match_dict in wl_matches_per_player)


class ShiftagoExpress(Shiftago):

    _WINNING_LINES_DETECTOR_4 = WinningLinesDetector(4)
    _WINNING_LINES_DETECTOR_5 = WinningLinesDetector(5)

    def __init__(self, *, orig: Optional['ShiftagoExpress'] = None, players: Optional[Sequence[Colour]] = None,
                 board: Optional[Dict[Slot, Colour]] = None) -> None:
        super().__init__(orig=orig, players=players, board=board)
        if orig is not None:
            self._game_over_condition = orig._game_over_condition
            self._winning_lines_detector = orig._winning_lines_detector
        else:
            if players is None:
                raise ValueError("Parameters 'players' is mandatory if 'orig' is None!")
            num_players = len(players)
            if 3 <= num_players <= 4:
                self._winning_lines_detector = self._WINNING_LINES_DETECTOR_4
            elif num_players == 2:
                self._winning_lines_detector = self._WINNING_LINES_DETECTOR_5
            else:
                raise ValueError("Illegal number of players: {0}".format(num_players))
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

        self._insert_marble(move.side, move.position)

        if self._has_current_player_won():
            self._game_over_condition = GameOverCondition(self._players[0])
        else:
            num_slots_per_colour = self.count_slots_per_colour()
            # check if there is a free slot left
            if sum(num_slots_per_colour.values()) < NUM_SLOTS_PER_SIDE * NUM_SLOTS_PER_SIDE:
                next_player = self._select_next_player()
                # check if selected player has one available marble at least
                if num_slots_per_colour[next_player] == NUM_MARBLES_PER_COLOUR:
                    self._game_over_condition = GameOverCondition()
            else:
                # all slots are occupied
                self._game_over_condition = GameOverCondition()
        if self._game_over_condition is not None:
            self.observer.notify_game_over()
        return self._game_over_condition

    def _has_current_player_won(self) -> bool:
        return len(self._winning_lines_detector.detect_winning_lines(self)[0]) > 0

    def detect_winning_lines(self, min_match_count: Optional[int] = None) -> Sequence[Dict[WinningLine, int]]:
        return self._winning_lines_detector.detect_winning_lines(self, min_match_count)

    def _select_next_player(self) -> Colour:
        self._players.rotate(-1)
        return self._players[0]

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'ShiftagoExpress':
        """Deserializes a JSON input stream to a ShiftagoExpress instance"""
        return ShiftagoDeser(cls).deserialize(input_stream)
