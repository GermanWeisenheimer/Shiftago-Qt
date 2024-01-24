# pylint: disable=consider-using-f-string
import copy
import unittest
from shiftago.core import NUM_SLOTS_PER_SIDE, Colour, Slot, Move, Side
from shiftago.core.express import ShiftagoExpress, ScoreAnalyzer
from tests import TestDataLoader


class ScoreAnalyzerTest(unittest.TestCase):

    def test_winning_lines_at(self):
        score_analyzer = ScoreAnalyzer(2)
        self.assertEqual(3, len(score_analyzer.winning_lines_at(Slot(0, 0))))
        self.assertEqual(4, len(score_analyzer.winning_lines_at(Slot(0, 3))))
        self.assertEqual(12, len(score_analyzer.winning_lines_at(Slot(3, 3))))
        self.assertEqual(5, len(score_analyzer.winning_lines_at(Slot(6, 2))))


class ShiftagoExpressTest(unittest.TestCase):

    def test_copy(self):
        with TestDataLoader(ShiftagoExpress, 'board1.json') as express_game:
            express_game2 = copy.copy(express_game)
            self.assertTrue(express_game2 is not express_game)
            self.assertEqual(express_game2.players, express_game.players)
            self.assertEqual(express_game2.current_player, express_game.current_player)
            for ver_pos in range(NUM_SLOTS_PER_SIDE):
                for hor_pos in range(NUM_SLOTS_PER_SIDE):
                    slot_pos = Slot(hor_pos, ver_pos)
                    self.assertEqual(express_game2.colour_at(slot_pos), express_game.colour_at(slot_pos))

    def test_apply_move(self):
        with TestDataLoader(ShiftagoExpress, 'board2.json') as express_game:
            express_game.apply_move(Move(Side.TOP, 2))
            self.assertEqual(Colour.GREEN, express_game.colour_at(Slot(2, 0)))
            self.assertEqual(Colour.ORANGE, express_game.colour_at(Slot(2, 1)))
            self.assertEqual(Colour.ORANGE, express_game.colour_at(Slot(2, 2)))
            self.assertEqual(Colour.GREEN, express_game.colour_at(Slot(2, 3)))
            express_game.apply_move(Move(Side.TOP, 6))
            self.assertEqual(Colour.ORANGE, express_game.colour_at(Slot(6, 0)))
            self.assertEqual(Colour.BLUE, express_game.colour_at(Slot(6, 1)))
            self.assertEqual(Colour.ORANGE, express_game.colour_at(Slot(6, 2)))
            express_game.apply_move(Move(Side.BOTTOM, 5))
            self.assertEqual(Colour.BLUE, express_game.colour_at(Slot(5, 6)))
            express_game.apply_move(Move(Side.BOTTOM, 5))
            self.assertEqual(Colour.BLUE, express_game.colour_at(Slot(5, 5)))
            self.assertEqual(Colour.GREEN, express_game.colour_at(Slot(5, 6)))
            express_game.apply_move(Move(Side.RIGHT, 2))
            self.assertEqual(Colour.BLUE, express_game.colour_at(Slot(0, 2)))
            self.assertEqual(Colour.ORANGE, express_game.colour_at(Slot(6, 2)))
            express_game.apply_move(Move(Side.LEFT, 4))
            express_game.apply_move(Move(Side.LEFT, 3))
            express_game.apply_move(Move(Side.LEFT, 3))
            self.assertEqual(Colour.ORANGE, express_game.colour_at(Slot(0, 3)))
            self.assertEqual(Colour.GREEN, express_game.colour_at(Slot(1, 3)))
            self.assertEqual(Colour.GREEN, express_game.colour_at(Slot(2, 3)))
            self.assertIsNone(express_game.colour_at(Slot(3, 3)))
            express_game.apply_move(Move(Side.LEFT, 3))
            self.assertEqual(Colour.BLUE, express_game.colour_at(Slot(0, 3)))
            self.assertEqual(Colour.ORANGE, express_game.colour_at(Slot(1, 3)))
            self.assertEqual(Colour.GREEN, express_game.colour_at(Slot(2, 3)))
            self.assertEqual(Colour.GREEN, express_game.colour_at(Slot(3, 3)))

    def test_analyze_line_match_scores(self):
        with TestDataLoader(ShiftagoExpress, 'board3.json') as express_game:
            blue_score, orange_score = express_game.analyze_line_match_scores()
            print("\nBLUE:")
            for match_count, score in blue_score.items():
                print("{0}: {1}".format(match_count, score))
            self.assertEqual(0, blue_score[5])
            self.assertEqual(1, blue_score[4])
            self.assertEqual(1, blue_score[3])
            self.assertEqual(1, blue_score[2])
            self.assertEqual(0, blue_score[1])
            print("ORANGE:")
            for match_count, score in orange_score.items():
                print("{0}: {1}".format(match_count, score))
            self.assertEqual(0, orange_score[5])
            self.assertEqual(2, orange_score[4])
            self.assertEqual(1, orange_score[3])
            self.assertEqual(0, orange_score[2])
            self.assertEqual(0, orange_score[1])
