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


class _MiniMaxStrategy(ABC):

    def __init__(self, alpha: float, beta: float) -> None:
        self._alpha = alpha
        self._beta = beta
        self._optimal_move: Optional[Move] = None

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def beta(self) -> float:
        return self._beta

    @property
    def optimal_move(self) -> Optional[Move]:
        return self._optimal_move

    @property
    def win_rating(self) -> float:
        return 1 if self.is_maximizing else -1

    @property
    @abstractmethod
    def is_maximizing(self) -> bool:
        pass

    @abstractmethod
    def compare(self, other_move: Move, other_rating: float) -> bool:
        pass


class AlphaBetaPruning(AIEngine[ShiftagoExpress]):

    class _Maximizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return True

        def compare(self, other_move: Move, other_rating: float) -> bool:
            if self._optimal_move is None or other_rating > self._alpha:
                self._optimal_move = other_move
                self._alpha = other_rating
            return self._alpha >= self._beta or self._alpha == self.win_rating

    class _Minimizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return False

        def compare(self, other_move: Move, other_rating: float) -> bool:
            if self._optimal_move is None or other_rating < self._beta:
                self._optimal_move = other_move
                self._beta = other_rating
            return self._beta <= self._alpha or self._beta == self.win_rating

    def __init__(self, skill_level=SkillLevel.ADVANCED) -> None:
        super().__init__(skill_level)
        self._skill_level = skill_level
        self._max_depth = 2 + skill_level.value

    def select_move(self, game_state: ShiftagoExpress) -> Move:
        assert len(game_state.players) == 2
        num_occupied_slots = game_state.count_occupied_slots()
        if num_occupied_slots > 1:
            self._max_depth = 2 + self._skill_level.value if num_occupied_slots >= 6 else 1
            move, node, num_visited_nodes = self.apply(game_state, 1, -math.inf, math.inf)
            _logger.debug("Selected move: %s (depth = %d, rating = %f, num_visited_nodes = %d)",
                          move, node.depth, node.rating, num_visited_nodes)
            return move
        move = random.choice(game_state.detect_all_possible_moves())
        _logger.debug("Selected random move: %s", move)
        return move

    def apply(self, game_state: ShiftagoExpress, depth: int, alpha: float, beta: float) \
            -> Tuple[Move, _Node, int]:
        current_strategy = self._Maximizer(alpha, beta) if depth % 2 == 1 else self._Minimizer(alpha, beta)
        possible_moves = game_state.detect_all_possible_moves()
        nodes = {move: self._eval_move(depth, current_strategy.win_rating, game_state, move)
                 for move in possible_moves}
        possible_moves.sort(key=lambda m: nodes[m].rating, reverse=current_strategy.is_maximizing)
        num_visited_nodes = 0
        if depth == 1:
            max_depth = self._max_depth if game_state.count_occupied_slots() >= 6 else 1
        else:
            max_depth = self._max_depth
        for current_move in possible_moves:
            current_node = nodes[current_move]
            if not current_node.is_leaf and depth < max_depth:
                _, child_node, child_num_visited = self.apply(current_node.new_game_state, depth + 1,
                                                              current_strategy.alpha, current_strategy.beta)
                num_visited_nodes += child_num_visited
                current_node.depth = child_node.depth
                current_node.rating = child_node.rating
            else:
                num_visited_nodes += 1
            if current_strategy.compare(current_move, current_node.rating):
                break  # cut-off!
        optimal_move = current_strategy.optimal_move
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
                rating += (len(current_player_result[i]) - len(opponent_result[i])) * \
                    _pow10(-(winning_line_length - i + 1)) * win_rating
        return _Node(cloned_game_state, is_leaf, depth, rating)
