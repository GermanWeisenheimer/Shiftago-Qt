from typing import Optional
from enum import Enum
from shiftago.core import Slot, Colour, Side
from shiftago.core.express import ShiftagoExpress
from shiftago.core.express_ai import AlphaBetaPruning
from shiftago.ui.board_view_model import BoardViewModel


class PlayerNature(Enum):

    HUMAN = 1
    ARTIFICIAL = 2


class ShiftagoExpressModel(BoardViewModel):

    def __init__(self, core_model: ShiftagoExpress) -> None:
        super().__init__()
        core_model.observer = self
        self._core_model = core_model
        self.ai_engine = AlphaBetaPruning()

    @property
    def core_model(self) -> ShiftagoExpress:
        return self._core_model

    @property
    def current_player(self) -> Optional[Colour]:
        return self._core_model.current_player

    @property
    def current_player_nature(self) -> Optional[PlayerNature]:
        if self._core_model.current_player:
            return self.player_nature_of(self._core_model.current_player)
        else:
            return None

    def player_nature_of(self, colour: Colour) -> PlayerNature:
        return PlayerNature.HUMAN if colour == Colour.BLUE else PlayerNature.ARTIFICIAL
    
    def colour_at(self, position: Slot) -> Optional[Colour]:
        return self._core_model.colour_at(position)

    def is_insertion_possible(self, side: Side, insert_pos: int) -> bool:
        return self._core_model.find_first_empty_slot(side, insert_pos) is not None
