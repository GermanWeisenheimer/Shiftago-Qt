from typing import List, Tuple
from shiftago.core import NUM_SLOTS_PER_SIDE, Slot, LineOrientation


class WinningLine:

    def __init__(self, orientation: LineOrientation, num_slots_in_line: int, slot_positions: List[Slot]) -> None:
        self._orientation = orientation
        if len(slot_positions) == num_slots_in_line:
            delta_hor_pos = slot_positions[1].hor_pos - slot_positions[0].hor_pos
            delta_ver_pos = slot_positions[1].ver_pos - slot_positions[0].ver_pos
            if orientation == LineOrientation.HORIZONTAL:
                if delta_hor_pos != 1:
                    raise ValueError("Slots not in a horizontal line!")
                if delta_ver_pos != 0:
                    raise ValueError("Slots not in a horizontal line!")
                for i in range(NUM_SLOTS_PER_SIDE - num_slots_in_line, num_slots_in_line):
                    if (slot_positions[i].hor_pos - slot_positions[i - 1].hor_pos != delta_hor_pos or
                            slot_positions[i].ver_pos - slot_positions[i - 1].ver_pos != delta_ver_pos):
                        raise ValueError("Slots not in a horizontal line!")
            elif orientation == LineOrientation.VERTICAL:
                if delta_hor_pos != 0:
                    raise ValueError("Slots not in a vertical line!")
                if delta_ver_pos != 1:
                    raise ValueError("Slots not in a vertical line!")
                for i in range(NUM_SLOTS_PER_SIDE - num_slots_in_line, num_slots_in_line):
                    if (slot_positions[i].hor_pos - slot_positions[i - 1].hor_pos != delta_hor_pos or
                            slot_positions[i].ver_pos - slot_positions[i - 1].ver_pos != delta_ver_pos):
                        raise ValueError("Slots not in a vertical line!")
            elif orientation == LineOrientation.DIAGONAL:
                if delta_hor_pos != 1:
                    raise ValueError("Slots not in a diagonal line!")
                if delta_ver_pos != 1 and delta_ver_pos != -1:
                    raise ValueError("Slots not in a vertical line!")
                for i in range(NUM_SLOTS_PER_SIDE, num_slots_in_line):
                    if (slot_positions[i].hor_pos - slot_positions[i - 1].hor_pos != delta_hor_pos or
                            slot_positions[i].ver_pos - slot_positions[i - 1].ver_pos != delta_ver_pos):
                        raise ValueError("Slots not in a diagonal line!")
            self._slot_positions = tuple(slot_positions)
        else:
            raise ValueError("Illegal number of slot positions: {0}".format(len(slot_positions)))

    def __eq__(self, other) -> bool:
        if isinstance(other, WinningLine):
            return self._slot_positions == other._slot_positions
        else:
            return False

    def __hash__(self) -> int:
        return hash(self._slot_positions)

    def __str__(self) -> str:
        return ",".join(str(sp) for sp in self._slot_positions)

    @property
    def orientation(self) -> LineOrientation:
        return self._orientation

    @property
    def slot_positions(self) -> Tuple[Slot]:
        return self._slot_positions

    @staticmethod
    def get_all(num_slots_in_line: int) -> List['WinningLine']:
        all_winning_line_ups = list()  # type: List[WinningLine]
        for ver_pos in range(0, NUM_SLOTS_PER_SIDE):
            for hor_pos_from in range(0, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slot_positions = list()  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slot_positions.append(Slot(hor_pos_from + i, ver_pos))
                all_winning_line_ups.append(WinningLine(
                    LineOrientation.HORIZONTAL, num_slots_in_line, slot_positions))
        for hor_pos in range(0, NUM_SLOTS_PER_SIDE):
            for ver_pos_from in range(0, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slot_positions = list()  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slot_positions.append(Slot(hor_pos, ver_pos_from + i))
                all_winning_line_ups.append(WinningLine(LineOrientation.VERTICAL, num_slots_in_line, slot_positions))
        for ver_pos in range(0, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
            hor_pos_from = 0
            for ver_pos_from in range(ver_pos, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slot_positions = list()  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slot_positions.append(Slot(hor_pos_from + i, ver_pos_from + i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slot_positions))
                hor_pos_from += 1
        for ver_pos in range(num_slots_in_line - 1, NUM_SLOTS_PER_SIDE):
            hor_pos_from = 0
            for ver_pos_from in range(ver_pos, num_slots_in_line - 2, -1):
                slot_positions = list()  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slot_positions.append(Slot(hor_pos_from + i, ver_pos_from - i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slot_positions))
                hor_pos_from += 1
        for hor_pos in range(1, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
            ver_pos_from = 0
            for hor_pos_from in range(hor_pos, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slot_positions = list()  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slot_positions.append(Slot(hor_pos_from + i, ver_pos_from + i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slot_positions))
                ver_pos_from += 1
        for hor_pos in range(1, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
            ver_pos_from = NUM_SLOTS_PER_SIDE - 1
            for hor_pos_from in range(hor_pos, NUM_SLOTS_PER_SIDE - num_slots_in_line + 1):
                slot_positions = list()  # type: List[Slot]
                for i in range(0, num_slots_in_line):
                    slot_positions.append(Slot(hor_pos_from + i, ver_pos_from - i))
                all_winning_line_ups.append(WinningLine(LineOrientation.DIAGONAL, num_slots_in_line, slot_positions))
                ver_pos_from -= 1
        return all_winning_line_ups
