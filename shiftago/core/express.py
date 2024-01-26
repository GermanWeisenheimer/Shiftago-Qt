# pylint: disable=consider-using-f-string
from typing import Dict, Sequence, Optional, TextIO
from shiftago.core import NUM_MARBLES_PER_COLOUR, NUM_SLOTS_PER_SIDE
from shiftago.core import ShiftagoDeser, Slot, Colour, Shiftago, Move, GameOverCondition, GameOverException
from .winning_line import WinningLine, WinningLinesDetector


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
