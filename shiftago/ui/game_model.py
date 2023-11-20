from typing import Optional
from enum import Enum
from shiftago.core import Colour, Move, GameOverCondition
from shiftago.core.express import ShiftagoExpress
from shiftago.core.express_ai import AlphaBetaPruning
from shiftago.ui.board_view_model import BoardViewModel


class PlayerNature(Enum):

    HUMAN = 1
    ARTIFICIAL = 2


class ShiftagoExpressModel(BoardViewModel):

    def __init__(self, core_model: ShiftagoExpress) -> None:
        super().__init__(core_model)
        core_model.observer = self
        self._core_model = core_model
        self._ai_engine = AlphaBetaPruning()

    @property
    def current_player_nature(self) -> Optional[PlayerNature]:
        if self._core_model.current_player:
            return self.player_nature_of(self._core_model.current_player)
        return None

    def player_nature_of(self, colour: Colour) -> PlayerNature:
        return PlayerNature.HUMAN if colour == Colour.BLUE else PlayerNature.ARTIFICIAL

    def apply_move(self, move: Move) -> Optional[GameOverCondition]:
        self._core_model.apply_move(move)

    def ai_select_move(self) -> Move:
        return self._ai_engine.select_move(self._core_model)

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._core_model.game_over_condition
