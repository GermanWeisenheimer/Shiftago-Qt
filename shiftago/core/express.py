# pylint: disable=consider-using-f-string
from typing import Tuple, List, Dict, Set, Optional, Callable, TextIO
from collections import defaultdict, OrderedDict
import json
from shiftago.core import NUM_MARBLES_PER_COLOUR, NUM_SLOTS_PER_SIDE
from shiftago.core import Slot, Colour, Shiftago, Move, GameOverCondition, JSONEncoder
from shiftago.core.winning_line import WinningLine


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
        if num_players >= 3 and num_players <= 4:
            self._winning_line_length = 4
        elif num_players == 2:
            self._winning_line_length = 5
        else:
            raise ValueError("Illegal number of players: {0}".format(num_players))
        all_winning_line_ups = WinningLine.get_all(self._winning_line_length)  # type: List[WinningLine]
        self._slot_to_lines = dict()  # type: Dict[Slot, Tuple[WinningLine,...]]
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot_pos = Slot(hor_pos, ver_pos)
                self._slot_to_lines[slot_pos] = tuple(
                    filter(lambda wlu: slot_pos in wlu.slots, all_winning_line_ups))

    @property
    def winning_line_length(self) -> int:
        return self._winning_line_length

    def winning_lines_at(self, slot: Slot) -> Tuple[WinningLine, ...]:
        return self._slot_to_lines[slot]

    def analyze(self, players: Tuple[Colour, ...],
                colour_at: Callable[[Slot], Optional[Colour]]) -> Dict[Colour, Dict[int, List[WinningLine]]]:
        intermediate_results = dict()  # type: Dict[Colour, Dict[WinningLine, int]]
        for p in players:
            intermediate_results[p] = defaultdict(lambda: 0)
        for ver_pos in range(NUM_SLOTS_PER_SIDE):
            for hor_pos in range(NUM_SLOTS_PER_SIDE):
                slot_pos = Slot(hor_pos, ver_pos)
                c = colour_at(slot_pos)
                if c is not None:
                    wl_dict = intermediate_results[c]  # type: Dict[WinningLine, int]
                    for wl in self.winning_lines_at(slot_pos):
                        wl_dict[wl] += 1
        results = dict()  # type: Dict[Colour, Dict[int, List[WinningLine]]]
        for p in players:
            results[p] = p_value = OrderedDict()  # Dict[int, List[WinningLine]]
            for i in range(self._winning_line_length, 1, -1):
                p_value[i] = list()
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
        return {wl for wl in wl_dict.keys() if wl_dict[wl] == self._winning_line_length}


class ShiftagoExpress(Shiftago):

    def __init__(self, players: Tuple[Colour, ...], *, current_player: Optional[Colour] = None,
                 board: Optional[Dict[Slot, Colour]] = None) -> None:
        super().__init__(players, current_player=current_player, board=board)
        self._board_analyzer = BoardAnalyzer(len(self.players))
        self._game_over_condition = None  # type: Optional[GameOverCondition]

    @property
    def winning_line_length(self) -> int:
        return self._board_analyzer.winning_line_length

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._game_over_condition

    def clone(self) -> 'ShiftagoExpress':
        return ShiftagoExpress(self._players, current_player=self._current_player, board=self._board.copy())

    def apply_move(self, move: Move) -> Optional[GameOverCondition]:
        self._insert_marble(move.side, move.position)

        if self.has_current_player_won():
            self._game_over_condition = GameOverCondition(self._current_player)
        else:
            num_slots_per_colour = self.count_slots_per_colour()  # type: Dict[Colour, int]
            # check if there is a free slot left
            if sum(num_slots_per_colour.values()) < NUM_SLOTS_PER_SIDE * NUM_SLOTS_PER_SIDE:
                next_player = self._select_next_player()
                # check if selected player has one available marble at least
                if num_slots_per_colour[next_player] < NUM_MARBLES_PER_COLOUR:
                    self._current_player = next_player
                else:
                    self._game_over_condition = GameOverCondition()
            else:
                # all slots are occupied
                self._game_over_condition = GameOverCondition()
        if self._game_over_condition is not None:
            self._current_player = None
            self.observer.notify_game_over()
        return self._game_over_condition

    def _select_next_player(self) -> Colour:
        current_player_index = self._players.index(self._current_player)
        if current_player_index + 1 < len(self._players):
            next_player_index = current_player_index + 1
        else:
            next_player_index = 0
        return self._players[next_player_index]

    def analyze(self) -> Dict[Colour, Dict[int, List[WinningLine]]]:
        return self._board_analyzer.analyze(self.players, self.colour_at)

    def has_current_player_won(self) -> bool:
        assert self._current_player
        return len(self._board_analyzer.detect_winning_lines(self._current_player, self.colour_at)) > 0

    @classmethod
    def deserialize(cls, input_stream: TextIO) -> 'ShiftagoExpress':
        """Deserializes a JSON input stream to a ShiftagoExpress instance"""
        def object_hook(json_dict: Dict) -> 'ShiftagoExpress':
            return cls(tuple(Colour(p) for p in json_dict[JSONEncoder.KEY_PLAYERS]),
                       current_player=Colour(json_dict[JSONEncoder.KEY_CURRENT_PLAYER]),
                       board=cls.deserialize_board(json_dict[JSONEncoder.KEY_BOARD]))
        return json.load(input_stream, object_hook=object_hook)
