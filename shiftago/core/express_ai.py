# pylint: disable=consider-using-f-string
import logging
import math
import random
import copy
from collections import defaultdict, namedtuple
from typing import List, Tuple, Optional, Sequence, Dict
from abc import ABC, abstractmethod
from functools import lru_cache
from .express import ShiftagoExpress, Move, GameOverCondition
from .ai_engine import AIEngine, SkillLevel

_logger = logging.getLogger(__name__)


def analyze_colour_placements(game_state: ShiftagoExpress) -> Sequence[Dict[int, int]]:
    winning_line_matches = game_state.detect_winning_lines(2)
    results = tuple(defaultdict(lambda: 0) for _ in winning_line_matches)  # type: Sequence[Dict[int, int]]
    for player_idx, match_groups_of_player in enumerate(results):
        for match_group_index in winning_line_matches[player_idx].values():
            match_groups_of_player[match_group_index] = match_groups_of_player[match_group_index] + 1
    return results


class Rating(namedtuple('Rating', 'value depth')):
    pass


class _Node:

    def __init__(self, from_game_state: ShiftagoExpress, move: Move) -> None:
        self._move = move
        self._target_game_state = copy.copy(from_game_state)
        self._game_over_condition = self._target_game_state.apply_move(move)

    def __str__(self) -> str:
        return "(move: {0}, is_leaf: {1})".format(self._move, self.is_leaf)

    def __hash__(self) -> int:
        return hash(self._move)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _Node):
            return self._move == other._move
        return False

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


class _MiniMaxStrategy(ABC):

    def __init__(self, alpha_beta: Tuple[float, float]) -> None:
        self._alpha, self._beta = alpha_beta
        if self.is_maximizing:
            self._win_rating_value = 1
        else:
            self._win_rating_value = -1
        self._optimal_rating = None  # type: Optional[Rating]

    @property
    def alpha_beta(self) -> Tuple[float, float]:
        return self._alpha, self._beta

    @property
    def optimal_rating(self) -> Rating:
        assert self._optimal_rating is not None
        return self._optimal_rating

    def sort_nodes(self, nodes: List) -> None:
        ratings = {node: self.evaluate(node) for node in nodes}
        nodes.sort(key=lambda n: ratings[n], reverse=self.is_maximizing)

    def evaluate(self, node: _Node) -> float:
        if node.game_over_condition is not None:
            if node.game_over_condition.winner is not None:
                return self._win_rating_value
            return 0.  # game ends in a draw
        opponent_placements, current_player_placements = analyze_colour_placements(node.target_game_state)
        winning_line_length = node.target_game_state.winning_line_length
        rating_value = 0.
        for i in range(winning_line_length, 1, -1):
            rating_value += (current_player_placements[i] - opponent_placements[i]) * \
                self._pow10(-(winning_line_length - i + 1)) * self._win_rating_value
        return rating_value

    @staticmethod
    @lru_cache(maxsize=10)
    def _pow10(exp: int) -> float:
        return math.pow(10, exp)

    def can_prune(self) -> bool:
        return self._alpha >= self._beta

    @property
    @abstractmethod
    def is_maximizing(self) -> bool:
        pass

    @abstractmethod
    def check_optimal(self, rating: Rating) -> bool:
        pass


class AlphaBetaPruning(AIEngine[ShiftagoExpress]):

    class _Maximizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return True

        def check_optimal(self, rating: Rating) -> bool:
            if self._optimal_rating is None or rating.value > self._optimal_rating.value:
                self._optimal_rating = rating
                if self._optimal_rating.value > self._alpha:
                    self._alpha = self._optimal_rating.value
                return True
            if rating.value == self._optimal_rating.value:
                if rating.depth < self._optimal_rating.depth if rating.value > 0. else \
                        rating. depth > self._optimal_rating.depth:
                    self._optimal_rating = rating
                    return True
            return False

    class _Minimizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return False

        def check_optimal(self, rating: Rating) -> bool:
            if self._optimal_rating is None or rating.value < self._optimal_rating.value:
                self._optimal_rating = rating
                if self._optimal_rating.value < self._beta:
                    self._beta = self._optimal_rating.value
                return True
            if rating.value == self._optimal_rating.value:
                if rating.depth < self._optimal_rating.depth if rating.value < 0. else \
                        rating.depth > self._optimal_rating.depth:
                    self._optimal_rating = rating
                    return True
            return False

    def __init__(self, skill_level=SkillLevel.ADVANCED) -> None:
        super().__init__(skill_level)
        self._max_depth = 2 + skill_level.value

    def select_move(self, game_state: ShiftagoExpress) -> Move:
        assert len(game_state.players) == 2
        if game_state.count_occupied_slots() > 1:
            move, rating = self._apply(game_state, 1, (-math.inf, math.inf))
            _logger.debug("Selected move: %s (%s)", move, rating)
            return move
        move = random.choice(game_state.detect_all_possible_moves())
        _logger.debug("Selected random move: %s", move)
        return move

    def _apply(self, game_state: ShiftagoExpress, depth: int, alpha_beta: Tuple[float, float]) \
            -> Tuple[Move, Rating]:
        strategy = self._Maximizer(alpha_beta) if depth % 2 == 1 else self._Minimizer(alpha_beta)
        nodes = [_Node(game_state, move) for move in game_state.detect_all_possible_moves()]
        if depth < self._max_depth:
            # pre-sorting massively increases the efficiency of pruning!
            strategy.sort_nodes(nodes)
        optimal_move = None
        for each_node in nodes:
            if each_node.is_leaf or depth == self._max_depth:
                current_rating = Rating(strategy.evaluate(each_node), depth)
            else:
                _, current_rating = \
                    self._apply(each_node.target_game_state, depth + 1, strategy.alpha_beta)
            if strategy.check_optimal(current_rating):
                optimal_move = each_node.move
                if strategy.can_prune():
                    break
        assert optimal_move is not None
        return optimal_move, strategy.optimal_rating
