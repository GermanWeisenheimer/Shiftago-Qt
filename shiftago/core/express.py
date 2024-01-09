# pylint: disable=consider-using-f-string
from typing import List, Dict, Set, Sequence, Optional, Callable, TextIO
from collections import defaultdict, OrderedDict
import json
from shiftago.core import NUM_MARBLES_PER_COLOUR, NUM_SLOTS_PER_SIDE
from shiftago.core import Slot, Colour, Shiftago, Move, GameOverCondition, JSONEncoder
from .winning_line import WinningLine


class BoardAnalyzer:

    _instances = {}  # type: Dict[int, BoardAnalyzer]

    def __new__(cls, num_players: int) -> 'BoardAnalyzer':
        instance = cls._instances.get(num_players, None)
        if instance is None:
            instance = super(BoardAnalyzer, cls).__new__(cls)
            instance.__init__(num_players)
            cls._instances[num_players] = instance
        return instance

    def __init__(self, num_players: int) -> None:
        if 3 <= num_players <= 4:
            self._winning_line_length = 4
        elif num_players == 2:
            self._winning_line_length = 5
        else:
            raise ValueError("Illegal number of players: {0}".format(num_players))
        all_winning_line_ups = WinningLine.get_all(self._winning_line_length)
        self._slot_to_lines = {slot: set(filter(lambda wlu: slot in wlu.slots,  # pylint: disable=cell-var-from-loop
                                                all_winning_line_ups))
                               for slot in [Slot(hor_pos, ver_pos) for ver_pos in range(NUM_SLOTS_PER_SIDE)
                                            for hor_pos in range(NUM_SLOTS_PER_SIDE)]}

    @property
    def winning_line_length(self) -> int:
        return self._winning_line_length

    def winning_lines_at(self, slot: Slot) -> Set[WinningLine]:
        return self._slot_to_lines[slot]

    def analyze(self, players: Sequence[Colour],
                colour_at: Callable[[Slot], Optional[Colour]]) -> Dict[Colour, Dict[int, List[WinningLine]]]:
        intermediate_results = {}  # type: Dict[Colour, Dict[WinningLine, int]]
        for p in players:
            intermediate_results[p] = defaultdict(lambda: 0)
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                c = colour_at(slot)
                if c is not None:
                    wl_dict = intermediate_results[c]
                    for wl in self.winning_lines_at(slot):
                        wl_dict[wl] += 1
        results = {}  # type: Dict[Colour, Dict[int, List[WinningLine]]]
        for p in players:
            results[p] = p_value = OrderedDict()  # Dict[int, List[WinningLine]]
            for i in range(self._winning_line_length, 1, -1):
                p_value[i] = []
            for winning_line, match_count in intermediate_results[p].items():
                if match_count > 1:
                    p_value[match_count].append(winning_line)
        return results

    def detect_winning_lines(self, player: Colour, colour_at: Callable[[Slot], Optional[Colour]]) -> Set[WinningLine]:
        wl_dict = defaultdict(lambda: 0)
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot = Slot(hor_pos, ver_pos)
                if colour_at(slot) is player:
                    for wl in self.winning_lines_at(slot):
                        wl_dict[wl] += 1
        return {wl for wl, match_count in wl_dict.items() if match_count == self._winning_line_length}


class ShiftagoExpress(Shiftago):

    def __init__(self, players: Sequence[Colour], board: Optional[Dict[Slot, Colour]] = None) -> None:
        super().__init__(players, board=board)
        self._board_analyzer = BoardAnalyzer(len(self.players))
        self._game_over_condition = None  # type: Optional[GameOverCondition]

    @property
    def winning_line_length(self) -> int:
        return self._board_analyzer.winning_line_length

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._game_over_condition

    def clone(self) -> 'ShiftagoExpress':
        return ShiftagoExpress(self._players, board=self._board.copy())

    def apply_move(self, move: Move) -> Optional[GameOverCondition]:
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
        return len(self._board_analyzer.detect_winning_lines(self._players[0], self.colour_at)) > 0

    def _select_next_player(self) -> Colour:
        self._players.rotate(-1)
        return self._players[0]

    def analyze(self) -> Dict[Colour, Dict[int, List[WinningLine]]]:
        return self._board_analyzer.analyze(self.players, self.colour_at)

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'ShiftagoExpress':
        """Deserializes a JSON input stream to a ShiftagoExpress instance"""
        def object_hook(json_dict: Dict) -> 'ShiftagoExpress':
            return cls([Colour(p) for p in json_dict[JSONEncoder.KEY_PLAYERS]],
                       board=cls.deserialize_board(json_dict[JSONEncoder.KEY_BOARD]))
        return json.load(input_stream, object_hook=object_hook)
