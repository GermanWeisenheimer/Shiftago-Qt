# pylint: disable=consider-using-f-string
import logging
import math
import random
import copy
from typing import Tuple, Optional
from abc import ABC, abstractmethod
from functools import lru_cache
from .express import ShiftagoExpress, Move
from .ai_engine import AIEngine, SkillLevel

_logger = logging.getLogger(__name__)


@lru_cache(maxsize=10)
def _pow10(exp: int) -> float:
    return math.pow(10, exp)


class _MiniMaxStrategy(ABC):

    def __init__(self, win_rating: float) -> None:
        if win_rating in (-1., 1.):
            self._win_rating = win_rating
        else:
            raise ValueError("Illegal win rating: {0}".format(win_rating))

    @property
    def win_rating(self) -> float:
        return self._win_rating

    @property
    @abstractmethod
    def is_maximizing(self) -> bool:
        pass


class _Node:

    def __init__(self, new_game_state: ShiftagoExpress, is_leaf: bool, depth: int, rating: float) -> None:
        self._new_game_state = new_game_state
        self._is_leaf = is_leaf
        self.depth = depth
        self.rating = rating

    def __str__(self) -> str:
        return "(depth: {0}, is_leaf: {1}, rating: {2})".format(self.depth, self.is_leaf, self.rating)

    @property
    def new_game_state(self) -> ShiftagoExpress:
        return self._new_game_state

    @property
    def is_leaf(self) -> bool:
        return self._is_leaf


class AlphaBetaPruning(AIEngine[ShiftagoExpress]):

    class _MiniMax:

        class Maximizer(_MiniMaxStrategy):

            def __init__(self) -> None:
                super().__init__(1.)

            @property
            def is_maximizing(self) -> bool:
                return True

        class Minimizer(_MiniMaxStrategy):

            def __init__(self) -> None:
                super().__init__(-1.)

            @property
            def is_maximizing(self) -> bool:
                return False

        def __init__(self, max_depth: int, num_occupied_slots: int) -> None:
            self._max_depth = max_depth if num_occupied_slots >= 6 else 1
            self._maximizer = self.Maximizer()
            self._minimizer = self.Minimizer()

        def current_strategy(self, depth: int) -> _MiniMaxStrategy:
            return self._maximizer if depth % 2 == 1 else self._minimizer

        def _should_recurse(self, node: _Node) -> bool:
            return not node.is_leaf and node.depth < self._max_depth

        def apply(self, game_state: ShiftagoExpress, depth: int, alpha: float, beta: float) \
                -> Tuple[Move, _Node, int]:
            current_strategy = self.current_strategy(depth)
            possible_moves = game_state.detect_all_possible_moves()
            nodes = {move: self._eval_move(depth, current_strategy.win_rating, game_state, move)
                     for move in possible_moves}
            possible_moves.sort(key=lambda m: nodes[m].rating, reverse=current_strategy.is_maximizing)
            num_visited_nodes = 0
            optimal_move = None  # type: Optional[Move]
            for current_move in possible_moves:
                current_node = nodes[current_move]
                if not current_node.is_leaf and depth < self._max_depth:
                    _, child_node, child_num_visited = self.apply(current_node.new_game_state,
                                                                  depth + 1, alpha, beta)
                    num_visited_nodes += child_num_visited
                    current_node.depth = child_node.depth
                    current_node.rating = child_node.rating
                else:
                    num_visited_nodes += 1
                if current_strategy.is_maximizing:
                    if optimal_move is None or current_node.rating > alpha:
                        optimal_move = current_move
                        alpha = current_node.rating
                        if alpha >= beta or alpha == current_strategy.win_rating:
                            break  # cut-off!
                else:
                    if optimal_move is None or current_node.rating < beta:
                        optimal_move = current_move
                        beta = current_node.rating
                        if beta <= alpha or beta == current_strategy.win_rating:
                            break  # cut-off!
            assert optimal_move is not None
            return optimal_move, nodes[optimal_move], num_visited_nodes

        def _eval_move(self, depth: int, win_rating: float, game_state: ShiftagoExpress, move: Move) -> _Node:
            is_leaf = False
            rating = 0.0
            cloned_game_state = copy.copy(game_state)
            game_end_condition = cloned_game_state.apply_move(move)
            if game_end_condition is not None:
                is_leaf = True
                if game_end_condition.winner is not None:
                    rating = win_rating
            else:
                player_results = cloned_game_state.analyze()
                current_player, current_opponent = game_state.players
                current_player_result = player_results[current_player]
                opponent_result = player_results[current_opponent]
                winning_line_length = game_state.winning_line_length
                for i in range(winning_line_length, 1, -1):
                    rating += (len(current_player_result[i]) - len(opponent_result[i])
                               ) * _pow10(-(winning_line_length - i + 1)) * win_rating
            return _Node(cloned_game_state, is_leaf, depth, rating)

    def __init__(self, skill_level=SkillLevel.ADVANCED) -> None:
        super().__init__(skill_level)
        self._max_depth = 2 + skill_level.value

    def select_move(self, game_state: ShiftagoExpress) -> Move:
        assert len(game_state.players) == 2
        num_occupied_slots = game_state.count_occupied_slots()
        if num_occupied_slots > 1:
            move, node, num_visited_nodes = self._MiniMax(
                self._max_depth, num_occupied_slots).apply(game_state, 1, -math.inf, math.inf)
            _logger.debug("Selected move: %s (depth = %d, rating = %f, num_visited_nodes = %d)",
                          move, node.depth, node.rating, num_visited_nodes)
            return move
        move = random.choice(game_state.detect_all_possible_moves())
        _logger.debug("Selected random move: %s", move)
        return move
