# pylint: disable=consider-using-f-string
import logging
import math
from typing import List, Dict, Tuple, Optional
from abc import ABC, abstractmethod
from random import randrange
from .express import ShiftagoExpress, Colour, Move, GameOverCondition, WinningLine

_logger = logging.getLogger(__name__)


def _current_opponent(game_state: ShiftagoExpress) -> Colour:
    players = game_state.players
    return players[1 if players.index(game_state.current_player) == 0 else 0]


class _MiniMaxStrategy(ABC):

    def __init__(self, win_rating: float) -> None:
        if win_rating == 1. or win_rating == -1.:
            self._win_rating = win_rating
        else:
            raise ValueError("Illegal win rating: {0}".format(win_rating))

    @property
    def win_rating(self) -> float:
        return self._win_rating

    @property
    @abstractmethod
    def reverse_order(self) -> bool:
        raise NotImplementedError


class _Maximizer(_MiniMaxStrategy):

    def __init__(self) -> None:
        super().__init__(1.)

    @property
    def reverse_order(self) -> bool:
        return True


class _Minimizer(_MiniMaxStrategy):

    def __init__(self) -> None:
        super().__init__(-1.)

    @property
    def reverse_order(self) -> bool:
        return False


class _Node:

    def __init__(self, new_game_state: ShiftagoExpress, is_leaf: bool, level: int, rating: float) -> None:
        self._new_game_state = new_game_state  # type: ShiftagoExpress
        self._is_leaf = is_leaf  # type: bool
        self.level = level  # type: int
        self.rating = rating  # type: float

    def __str__(self) -> str:
        return "(level: {0}, is_leaf: {1}, rating: {2})".format(self.level, self.is_leaf, self.rating)

    @property
    def new_game_state(self) -> ShiftagoExpress:
        return self._new_game_state

    @property
    def is_leaf(self) -> bool:
        return self._is_leaf


class AlphaBetaPruning:

    def __init__(self, max_depth=3) -> None:
        self._player_strategies = {}  # type: Dict[Colour, _MiniMaxStrategy]
        if max_depth < 1 or max_depth > 4:
            raise ValueError("Illegal max_depth: {0}".format(max_depth))
        self._max_depth = max_depth

    def select_move(self, game_state: ShiftagoExpress) -> Move:
        assert len(game_state.players) == 2
        assert game_state.current_player, "No current player!"
        self._player_strategies[game_state.current_player] = _Maximizer()
        self._player_strategies[_current_opponent(game_state)] = _Minimizer()
        move, node, num_visited_nodes = self._apply_mini_max(game_state, 1, -math.inf, math.inf)
        _logger.debug("Selected move: %s (level = %d, rating = %f, num_visited_nodes = %d)",
                      move, node.level, node.rating, num_visited_nodes)
        return move

    def _apply_mini_max(self, game_state: ShiftagoExpress, level: int,
                        alpha: float, beta: float) -> Tuple[Move, _Node, int]:
        num_occupied_slots = game_state.count_occupied_slots()
        assert game_state.current_player, "No current player!"
        current_strategy = self._player_strategies[game_state.current_player]  # type: _MiniMaxStrategy
        possible_moves = game_state.detect_all_possible_moves()
        nodes = {move: self._eval_move(current_strategy, level, game_state, move)
                 for move in possible_moves}  # type: Dict[Move, _Node]
        if num_occupied_slots <= 1:
            random_move = possible_moves[randrange(len(possible_moves))]
            return random_move, nodes[random_move], 1
        possible_moves.sort(key=lambda m: nodes[m].rating, reverse=current_strategy.reverse_order)
        max_depth = self._determine_max_depth(num_occupied_slots)  # type: int
        num_visited_nodes = 0  # type: int
        optimal_move = None  # type: Optional[Move]
        for current_move in possible_moves:
            current_node = nodes[current_move]  # type: _Node
            if not current_node.is_leaf and level < max_depth:
                _, child_node, child_num_visited = self._apply_mini_max(current_node.new_game_state, level + 1,
                                                                        alpha, beta)
                num_visited_nodes += child_num_visited
                current_node.level = child_node.level
                current_node.rating = child_node.rating
            else:
                num_visited_nodes += 1
            if isinstance(current_strategy, _Maximizer):
                if optimal_move is None or current_node.rating > alpha:
                    optimal_move = current_move
                    alpha = current_node.rating
                    if alpha >= beta or alpha == current_strategy.win_rating:
                        break  # cut-off!
            else:
                assert isinstance(current_strategy, _Minimizer)
                if optimal_move is None or current_node.rating < beta:
                    optimal_move = current_move
                    beta = current_node.rating
                    if beta <= alpha or beta == current_strategy.win_rating:
                        break  # cut-off!
        assert optimal_move is not None
        return optimal_move, nodes[optimal_move], num_visited_nodes

    def _determine_max_depth(self, num_occupied_slots: int) -> int:
        return 1 if num_occupied_slots < 6 else self._max_depth

    def _eval_move(self, current_strategy: _MiniMaxStrategy, level: int, game_state: ShiftagoExpress,
                   move: Move) -> _Node:
        is_leaf = False  # type: bool
        rating = 0.0  # type: float
        cloned_game_state = game_state.clone()  # type: ShiftagoExpress
        game_end_condition = cloned_game_state.apply_move(move)  # type: Optional[GameOverCondition]
        if game_end_condition is not None:
            is_leaf = True
            if game_end_condition.winner is not None:
                rating = current_strategy.win_rating
        else:
            player_results = cloned_game_state.analyze()  # type: Dict[Colour, Dict[int, List[WinningLine]]]
            assert game_state.current_player, "No current player!"
            current_player_result = player_results[game_state.current_player]
            opponent_result = player_results[_current_opponent(game_state)]
            winning_line_length = game_state.winning_line_length
            win_rating = current_strategy.win_rating
            for i in range(winning_line_length, 1, -1):
                rating += (len(current_player_result[i]) - len(opponent_result[i])
                           ) * math.pow(10, -(winning_line_length - i + 1)) * win_rating
        return _Node(cloned_game_state, is_leaf, level, rating)
