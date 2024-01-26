# pylint: disable=consider-using-f-string
from typing import List, Tuple, Dict, Set, Sequence, Optional
from collections import defaultdict
from shiftago.core import NUM_SLOTS_PER_SIDE, Slot, Shiftago, LineOrientation


class WinningLine:

    def __init__(self, orientation: LineOrientation, num_slots_in_line: int, slots: List[Slot]) -> None:
        self._orientation = orientation
        if len(slots) == num_slots_in_line:
            delta_hor_pos = slots[1].hor_pos - slots[0].hor_pos
            delta_ver_pos = slots[1].ver_pos - slots[0].ver_pos
            if orientation == LineOrientation.HORIZONTAL:
                if delta_hor_pos != 1:
                    raise ValueError("Slots not in a horizontal line!")
                if delta_ver_pos != 0:
                    raise ValueError("Slots not in a horizontal line!")
                for i in range(NUM_SLOTS_PER_SIDE - num_slots_in_line, num_slots_in_line):
                    if (slots[i].hor_pos - slots[i - 1].hor_pos != delta_hor_pos or
                            slots[i].ver_pos - slots[i - 1].ver_pos != delta_ver_pos):
                        raise ValueError("Slots not in a horizontal line!")
            elif orientation == LineOrientation.VERTICAL:
                if delta_hor_pos != 0:
                    raise ValueError("Slots not in a vertical line!")
                if delta_ver_pos != 1:
                    raise ValueError("Slots not in a vertical line!")
                for i in range(NUM_SLOTS_PER_SIDE - num_slots_in_line, num_slots_in_line):
                    if (slots[i].hor_pos - slots[i - 1].hor_pos != delta_hor_pos or
                            slots[i].ver_pos - slots[i - 1].ver_pos != delta_ver_pos):
                        raise ValueError("Slots not in a vertical line!")
            elif orientation == LineOrientation.DIAGONAL:
                if delta_hor_pos != 1:
                    raise ValueError("Slots not in a diagonal line!")
                if delta_ver_pos not in (1, -1):
                    raise ValueError("Slots not in a vertical line!")
                for i in range(NUM_SLOTS_PER_SIDE, num_slots_in_line):
                    if (slots[i].hor_pos - slots[i - 1].hor_pos != delta_hor_pos or
                            slots[i].ver_pos - slots[i - 1].ver_pos != delta_ver_pos):
                        raise ValueError("Slots not in a diagonal line!")
            self._slots = tuple(slots)
        else:
            raise ValueError("Illegal number of slot positions: {0}".format(len(slots)))

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
    def get_all(num_slots_in_line: int) -> List['WinningLine']:
        all_winning_line_ups = []  # type: List[WinningLine]
        for ver_pos in range(0, NUM_SLOTS_PER_SIDE):
            for hor_pos_from in range(0, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slots = []  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slots.append(Slot(hor_pos_from + i, ver_pos))
                all_winning_line_ups.append(WinningLine(
                    LineOrientation.HORIZONTAL, num_slots_in_line, slots))
        for hor_pos in range(0, NUM_SLOTS_PER_SIDE):
            for ver_pos_from in range(0, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slots = []  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slots.append(Slot(hor_pos, ver_pos_from + i))
                all_winning_line_ups.append(WinningLine(LineOrientation.VERTICAL, num_slots_in_line, slots))
        for ver_pos in range(0, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
            hor_pos_from = 0
            for ver_pos_from in range(ver_pos, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slots = []  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slots.append(Slot(hor_pos_from + i, ver_pos_from + i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slots))
                hor_pos_from += 1
        for ver_pos in range(num_slots_in_line - 1, NUM_SLOTS_PER_SIDE):
            hor_pos_from = 0
            for ver_pos_from in range(ver_pos, num_slots_in_line - 2, -1):
                slots = []  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slots.append(Slot(hor_pos_from + i, ver_pos_from - i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slots))
                hor_pos_from += 1
        for hor_pos in range(1, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
            ver_pos_from = 0
            for hor_pos_from in range(hor_pos, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slots = []  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slots.append(Slot(hor_pos_from + i, ver_pos_from + i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slots))
                ver_pos_from += 1
        for hor_pos in range(1, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
            ver_pos_from = NUM_SLOTS_PER_SIDE - 1
            for hor_pos_from in range(hor_pos, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slots = []  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slots.append(Slot(hor_pos_from + i, ver_pos_from - i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slots))
                ver_pos_from -= 1
        return all_winning_line_ups


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
