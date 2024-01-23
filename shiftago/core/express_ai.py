# pylint: disable=consider-using-f-string
import logging
import math
import random
import copy
from typing import Tuple, Optional
from abc import ABC, abstractmethod
from functools import lru_cache
from .express import ShiftagoExpress, Move, GameOverCondition
from .ai_engine import AIEngine, SkillLevel

_logger = logging.getLogger(__name__)


@lru_cache(maxsize=10)
def _pow10(exp: int) -> float:
    return math.pow(10, exp)


class _Node:

    def __init__(self, from_game_state: ShiftagoExpress, move: Move) -> None:
        self._move = move
        self._target_game_state = copy.copy(from_game_state)
        self._game_over_condition = self._target_game_state.apply_move(move)
        self.rating = 0.

    def __str__(self) -> str:
        return "(is_leaf: {0}, rating: {1})".format(self.is_leaf, self.rating)

    @property
    def move(self) -> Move:
        return self._move

    @property
    def target_game_state(self) -> ShiftagoExpress:
        return self._target_game_state

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        return self._game_over_condition

    @property
    def is_leaf(self) -> bool:
        return self._game_over_condition is not None

    def evaluate(self, win_rating: float):
        if self._game_over_condition is not None:
            if self._game_over_condition.winner is not None:
                self.rating = win_rating
            return
        player_results = self._target_game_state.analyze()
        current_opponent, current_player = self._target_game_state.players
        current_player_result = player_results[current_player]
        opponent_result = player_results[current_opponent]
        winning_line_length = self._target_game_state.winning_line_length
        for i in range(winning_line_length, 1, -1):
            self.rating += (len(current_player_result[i]) - len(opponent_result[i])) * \
                _pow10(-(winning_line_length - i + 1)) * win_rating


class _MiniMaxStrategy(ABC):

    def __init__(self, alpha_beta: Tuple[float, float]) -> None:
        self._alpha, self._beta = alpha_beta
        if self.is_maximizing:
            self._win_rating = 1
            self._optimal_rating = -math.inf
        else:
            self._win_rating = -1
            self._optimal_rating = math.inf

    @property
    def alpha_beta(self) -> Tuple[float, float]:
        return self._alpha, self._beta

    @property
    def win_rating(self) -> float:
        return self._win_rating

    def can_cut_off(self) -> bool:
        return self._alpha >= self._beta

    @property
    @abstractmethod
    def is_maximizing(self) -> bool:
        pass

    @abstractmethod
    def check_optimal(self, node: _Node) -> bool:
        pass


class AlphaBetaPruning(AIEngine[ShiftagoExpress]):

    class _Maximizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return True

        def check_optimal(self, node: _Node) -> bool:
            if node.rating > self._optimal_rating:
                self._optimal_rating = node.rating
                if self._optimal_rating > self._alpha:
                    self._alpha = self._optimal_rating
                return True
            return False

    class _Minimizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return False

        def check_optimal(self, node: _Node) -> bool:
            if node.rating < self._optimal_rating:
                self._optimal_rating = node.rating
                if self._optimal_rating < self._beta:
                    self._beta = self._optimal_rating
                return True
            return False

    def __init__(self, skill_level=SkillLevel.ADVANCED) -> None:
        super().__init__(skill_level)
        self._max_depth = 2 + skill_level.value

    def select_move(self, game_state: ShiftagoExpress) -> Move:
        assert len(game_state.players) == 2
        num_occupied_slots = game_state.count_occupied_slots()
        if num_occupied_slots > 1:
            move, rating, num_visited_nodes = self._apply(game_state, 1, (-math.inf, math.inf))
            _logger.debug("Selected move: %s (rating = %f, num_visited_nodes = %d)",
                          move, rating, num_visited_nodes)
            return move
        move = random.choice(game_state.detect_all_possible_moves())
        _logger.debug("Selected random move: %s", move)
        return move

    def _apply(self, game_state: ShiftagoExpress, depth: int, alpha_beta: Tuple[float, float]) \
            -> Tuple[Move, float, int]:
        strategy = self._Maximizer(alpha_beta) if depth % 2 == 1 else self._Minimizer(alpha_beta)
        nodes = [_Node(game_state, move) for move in game_state.detect_all_possible_moves()]
        if depth < self._max_depth:
            for each_node in nodes:
                each_node.evaluate(strategy.win_rating)
            # pre-sorting massively increases the efficiency of pruning!
            nodes.sort(key=lambda n: n.rating, reverse=strategy.is_maximizing)
        num_visited_nodes = 0
        optimal_node = None  # type: Optional[_Node]
        for each_node in nodes:
            if depth == self._max_depth:
                each_node.evaluate(strategy.win_rating)
                num_visited_nodes += 1
            elif not each_node.is_leaf:
                _, each_node.rating, child_num_visited = self._apply(each_node.target_game_state,
                                                                     depth + 1, strategy.alpha_beta)
                num_visited_nodes += child_num_visited
            if strategy.check_optimal(each_node):
                optimal_node = each_node
                if strategy.can_cut_off():
                    break
        assert optimal_node is not None
        return optimal_node.move, optimal_node.rating, num_visited_nodes
