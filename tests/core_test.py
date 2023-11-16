import unittest
from unittest.mock import patch
from shiftago.core import Shiftago, Slot, Side
from tests import TestDataLoader


class SideTest(unittest.TestCase):

    def test_left(self):
        self.assertEqual(0, Side.LEFT.position)
        self.assertFalse(Side.LEFT.is_horizontal)
        self.assertTrue(Side.LEFT.is_vertical)
        self.assertEqual(1, Side.LEFT.shift_direction)
        self.assertEqual(Side.RIGHT, Side.LEFT.opposite)

    def test_right(self):
        self.assertEqual(6, Side.RIGHT.position)
        self.assertFalse(Side.RIGHT.is_horizontal)
        self.assertTrue(Side.RIGHT.is_vertical)
        self.assertEqual(-1, Side.RIGHT.shift_direction)
        self.assertEqual(Side.LEFT, Side.RIGHT.opposite)

    def test_top(self):
        self.assertEqual(0, Side.TOP.position)
        self.assertTrue(Side.TOP.is_horizontal)
        self.assertFalse(Side.TOP.is_vertical)
        self.assertEqual(1, Side.TOP.shift_direction)
        self.assertEqual(Side.BOTTOM, Side.TOP.opposite)

    def test_bottom(self):
        self.assertEqual(6, Side.BOTTOM.position)
        self.assertTrue(Side.BOTTOM.is_horizontal)
        self.assertFalse(Side.BOTTOM.is_vertical)
        self.assertEqual(-1, Side.BOTTOM.shift_direction)
        self.assertEqual(Side.TOP, Side.BOTTOM.opposite)

    def test_opposite(self):
        self.assertEqual(Side.RIGHT, Side.LEFT.opposite)
        self.assertEqual(Side.LEFT, Side.RIGHT.opposite)
        self.assertEqual(Side.BOTTOM, Side.TOP.opposite)
        self.assertEqual(Side.TOP, Side.BOTTOM.opposite)


class SlotTest(unittest.TestCase):

    def test__str__(self):
        self.assertEqual("[5,6]", str(Slot(5, 6)))

    def test__eq__(self):
        slot_pos1 = Slot(4, 3)  # type: Slot
        self.assertEqual(4, slot_pos1.hor_pos)
        self.assertEqual(3, slot_pos1.ver_pos)
        slot_pos2 = Slot(4, 3)  # type: Slot
        self.assertTrue(slot_pos1 is slot_pos2)
        self.assertEqual(slot_pos2, slot_pos1)

    def test__lt__(self):
        slot_pos1 = Slot(4, 3)  # type: Slot
        self.assertTrue(Slot(3, 3) < slot_pos1)
        self.assertFalse(Slot(5, 3) < slot_pos1)
        self.assertTrue(Slot(5, 2) < slot_pos1)
        self.assertFalse(Slot(3, 4) < slot_pos1)

    def test_on_edge(self):
        self.assertEqual(Slot(0, 0), Slot.on_edge(Side.LEFT, 0))
        self.assertEqual(Slot(0, 6), Slot.on_edge(Side.LEFT, 6))
        self.assertEqual(Slot(6, 0), Slot.on_edge(Side.RIGHT, 0))
        self.assertEqual(Slot(6, 6), Slot.on_edge(Side.RIGHT, 6))
        self.assertEqual(Slot(0, 0), Slot.on_edge(Side.TOP, 0))
        self.assertEqual(Slot(6, 0), Slot.on_edge(Side.TOP, 6))
        self.assertEqual(Slot(0, 6), Slot.on_edge(Side.BOTTOM, 0))
        self.assertEqual(Slot(6, 6), Slot.on_edge(Side.BOTTOM, 6))

    def test_neighbour(self):
        self.assertEqual(Slot(1, 3), Slot(0, 3).neighbour(Side.RIGHT))


@patch("shiftago.core.Shiftago.__abstractmethods__", set())
class ShiftagoTest(unittest.TestCase):

    def test__str__(self):
        with TestDataLoader(Shiftago, 'board1.json') as shiftago_game:
            self.assertEqual("""
_|_|_|_|_|_|_
_|_|_|_|_|_|_
_|_|_|_|_|_|O
_|_|_|_|_|_|O
B|B|B|G|_|_|O
_|_|_|G|_|_|_
_|_|_|G|_|_|_""".lstrip(), str(shiftago_game))

    def test_find_first_empty_slot(self):
        with TestDataLoader(Shiftago, 'board2.json') as shiftago_game:
            self.assertTrue(shiftago_game.find_first_empty_slot(Side.LEFT, 0) is None)
            self.assertTrue(shiftago_game.find_first_empty_slot(Side.RIGHT, 0) is None)
            self.assertEqual(Slot(6, 1), shiftago_game.find_first_empty_slot(Side.LEFT, 1))
            self.assertEqual(Slot(6, 1), shiftago_game.find_first_empty_slot(Side.RIGHT, 1))
            self.assertEqual(Slot(0, 2), shiftago_game.find_first_empty_slot(Side.LEFT, 2))
            self.assertEqual(Slot(0, 2), shiftago_game.find_first_empty_slot(Side.RIGHT, 2))
            self.assertEqual(Slot(0, 2), shiftago_game.find_first_empty_slot(Side.TOP, 0))
            self.assertEqual(Slot(0, 6), shiftago_game.find_first_empty_slot(Side.BOTTOM, 0))
            self.assertEqual(Slot(1, 3), shiftago_game.find_first_empty_slot(Side.TOP, 1))
            self.assertEqual(Slot(1, 6), shiftago_game.find_first_empty_slot(Side.BOTTOM, 1))
            self.assertEqual(Slot(6, 1), shiftago_game.find_first_empty_slot(Side.TOP, 6))
            self.assertEqual(Slot(6, 6), shiftago_game.find_first_empty_slot(Side.BOTTOM, 6))

    def test_count_occupied_slots(self):
        with TestDataLoader(Shiftago, 'board2.json') as shiftago_game:
            self.assertEqual(19, shiftago_game.count_occupied_slots())

    def test_detect_all_possible_moves(self):
        with TestDataLoader(Shiftago, 'board2.json') as shiftago_game:
            possible_moves = shiftago_game.detect_all_possible_moves()
            self.assertEqual(26, len(possible_moves))


if __name__ == '__main__':
    unittest.main()
