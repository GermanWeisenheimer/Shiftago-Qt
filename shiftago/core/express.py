# pylint: disable=consider-using-f-string
from typing import Dict, Set, Sequence, Optional, Callable, TextIO
from collections import defaultdict
from shiftago.core import NUM_MARBLES_PER_COLOUR, NUM_SLOTS_PER_SIDE
from shiftago.core import ShiftagoDeser, Slot, Colour, Shiftago, Move, GameOverCondition, GameOverException
from .winning_line import WinningLine


class ExpressBoardAnalyzer:

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

    def analyze_colour_placements(self, players: Sequence[Colour],
                                  colour_at: Callable[[Slot], Optional[Colour]]) -> Sequence[Dict[int, int]]:
        winning_line_matches = \
            {p: defaultdict(lambda: 0) for p in players}  # type: Dict[Colour, Dict[WinningLine, int]]
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                c = colour_at(slot)
                if c is not None:
                    line_match_dict = winning_line_matches[c]
                    for wl in self._slot_to_lines[slot]:
                        line_match_dict[wl] += 1
        results = tuple(defaultdict(lambda: 0) for _ in players)  # type: Sequence[Dict[int, int]]
        for i, player in enumerate(players):
            match_groups_of_player = results[i]
            for match_group_index in winning_line_matches[player].values():
                if match_group_index > 1:
                    match_groups_of_player[match_group_index] = match_groups_of_player[match_group_index] + 1
        return results

    def detect_winning_lines(self, player: Colour, colour_at: Callable[[Slot], Optional[Colour]]) \
            -> Set[WinningLine]:
        wl_dict = defaultdict(lambda: 0)
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                if colour_at(slot) is player:
                    for wl in self._slot_to_lines[slot]:
                        wl_dict[wl] += 1
        return {wl for wl, match_count in wl_dict.items() if match_count == self._winning_line_length}


class ShiftagoExpress(Shiftago):

    _BOARD_ANALYZER_4 = ExpressBoardAnalyzer(4)
    _BOARD_ANALYZER_5 = ExpressBoardAnalyzer(5)

    def __init__(self, *, orig: Optional['ShiftagoExpress'] = None, players: Optional[Sequence[Colour]] = None,
                 board: Optional[Dict[Slot, Colour]] = None) -> None:
        super().__init__(orig=orig, players=players, board=board)
        if orig is not None:
            self._board_analyzer = orig._board_analyzer
            self._game_over_condition = orig._game_over_condition
        else:
            if players is None:
                raise ValueError("Parameters 'players' is mandatory if 'orig' is None!")
            num_players = len(players)
            if 3 <= num_players <= 4:
                self._board_analyzer = self._BOARD_ANALYZER_4
            elif num_players == 2:
                self._board_analyzer = self._BOARD_ANALYZER_5
            else:
                raise ValueError("Illegal number of players: {0}".format(num_players))
            self._game_over_condition = None

    @property
    def winning_line_length(self) -> int:
        return self._board_analyzer.winning_line_length

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

    def analyze_colour_placements(self) -> Sequence[Dict[int, int]]:
        return self._board_analyzer.analyze_colour_placements(self._players, self.colour_at)

    def _has_current_player_won(self) -> bool:
        return len(self._board_analyzer.detect_winning_lines(self._players[0], self.colour_at)) > 0

    def _select_next_player(self) -> Colour:
        self._players.rotate(-1)
        return self._players[0]

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'ShiftagoExpress':
        """Deserializes a JSON input stream to a ShiftagoExpress instance"""
        return ShiftagoDeser(cls).deserialize(input_stream)
