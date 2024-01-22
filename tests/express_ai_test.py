# pylint: disable=consider-using-f-string
import unittest
import logging
from shiftago.core import Colour, Side, Move
from shiftago.core.express import ShiftagoExpress
from shiftago.core.express_ai import SkillLevel, AlphaBetaPruning
from tests import TestDataLoader


class AlphaBetaPruningTest(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s,%(msecs)03d %(levelname)s - %(message)s',
                            datefmt='%H:%M:%S',
                            handlers=[logging.StreamHandler()])

    def test_alpha_beta_pruning_empty_board(self):
        express_game = ShiftagoExpress(players=(Colour.BLUE, Colour.ORANGE))
        move = AlphaBetaPruning().select_move(express_game)
        express_game.apply_move(move)
        print(express_game)

    def test_1_alpha_beta_pruning(self):
        with TestDataLoader(ShiftagoExpress, 'express_ai_test1.json') as express_game:
            print("\n{0}".format(express_game))
            move = AlphaBetaPruning().select_move(express_game)
            self.assertIn(move, (Move(Side.BOTTOM, 1), Move(Side.BOTTOM, 2), Move(Side.BOTTOM, 4)))
            print("Move: {0}".format(move))

    def test_2_alpha_beta_pruning(self):
        with TestDataLoader(ShiftagoExpress, 'express_ai_test2.json') as express_game:
            print("\n{0}".format(express_game))
            for skill_level in (SkillLevel.EXPERT, SkillLevel.GRANDMASTER):
                move = AlphaBetaPruning(skill_level).select_move(express_game)
                self.assertIn(move, (Move(Side.TOP, 1), Move(Side.TOP, 4)))
                print("Move: {0}".format(move))
