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
        self._target_game_state = copy.copy(from_game_state)
        self._game_over_condition = self._target_game_state.apply_move(move)
        self.rating = 0.

    def __str__(self) -> str:
        return "(is_leaf: {0}, rating: {1})".format(self.is_leaf, self.rating)

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

    def __init__(self, alpha: float, beta: float) -> None:
        self._alpha = alpha
        self._beta = beta
        self._optimal_move = None  # type: Optional[Move]
        if self.is_maximizing:
            self._win_rating = 1
            self._optimal_rating = -math.inf
        else:
            self._win_rating = -1
            self._optimal_rating = math.inf

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def beta(self) -> float:
        return self._beta

    @property
    def optimal_move(self) -> Move:
        assert self._optimal_move is not None
        return self._optimal_move

    @property
    def optimal_rating(self) -> float:
        return self._optimal_rating

    def should_cut_off(self) -> bool:
        return self._alpha >= self._beta

    def eval_move(self, game_state: ShiftagoExpress, move: Move) -> _Node:
        node = _Node(game_state, move)
        game_over_condition = node.game_over_condition
        if game_over_condition is not None:
            if game_over_condition.winner is not None:
                node.rating = self._win_rating
            return node
        player_results = node.target_game_state.analyze()
        current_player, current_opponent = game_state.players
        current_player_result = player_results[current_player]
        opponent_result = player_results[current_opponent]
        winning_line_length = game_state.winning_line_length
        for i in range(winning_line_length, 1, -1):
            node.rating += (len(current_player_result[i]) - len(opponent_result[i])) * \
                _pow10(-(winning_line_length - i + 1)) * self._win_rating
        return node

    @property
    @abstractmethod
    def is_maximizing(self) -> bool:
        pass

    @abstractmethod
    def update_optimal_move(self, move: Move, rating: float) -> bool:
        pass


class AlphaBetaPruning(AIEngine[ShiftagoExpress]):

    class _Maximizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return True

        def update_optimal_move(self, move: Move, rating: float) -> bool:
            if rating > self._optimal_rating:
                self._optimal_move = move
                self._optimal_rating = rating
                if self._optimal_rating > self._alpha:
                    self._alpha = self._optimal_rating
                return True
            return False

    class _Minimizer(_MiniMaxStrategy):

        @property
        def is_maximizing(self) -> bool:
            return False

        def update_optimal_move(self, move: Move, rating: float) -> bool:
            if rating < self._optimal_rating:
                self._optimal_move = move
                self._optimal_rating = rating
                if self._optimal_rating < self._beta:
                    self._beta = self._optimal_rating
                return True
            return False

    def __init__(self, skill_level=SkillLevel.ADVANCED) -> None:
        super().__init__(skill_level)
        self._skill_level = skill_level
        self._max_depth = 2 + skill_level.value

    def select_move(self, game_state: ShiftagoExpress) -> Move:
        assert len(game_state.players) == 2
        num_occupied_slots = game_state.count_occupied_slots()
        if num_occupied_slots > 1:
            move, rating, num_visited_nodes = self._apply(game_state, 1, -math.inf, math.inf)
            _logger.debug("Selected move: %s (rating = %f, num_visited_nodes = %d)",
                          move, rating, num_visited_nodes)
            return move
        move = random.choice(game_state.detect_all_possible_moves())
        _logger.debug("Selected random move: %s", move)
        return move

    def _apply(self, game_state: ShiftagoExpress, depth: int, alpha: float, beta: float) \
            -> Tuple[Move, float, int]:
        strategy = self._Maximizer(alpha, beta) if depth % 2 == 1 else self._Minimizer(alpha, beta)
        possible_moves = game_state.detect_all_possible_moves()
        nodes = {move: strategy.eval_move(game_state, move) for move in possible_moves}
        possible_moves.sort(key=lambda m: nodes[m].rating, reverse=strategy.is_maximizing)
        num_visited_nodes = 0
        for current_move in possible_moves:
            num_visited_nodes += 1
            current_node = nodes[current_move]
            current_rating = current_node.rating
            if not current_node.is_leaf and depth < self._max_depth:
                _, current_rating, child_num_visited = self._apply(current_node.target_game_state, depth + 1,
                                                                   strategy.alpha, strategy.beta)
                num_visited_nodes += child_num_visited
            if strategy.update_optimal_move(current_move, current_rating) and strategy.should_cut_off():
                break
        return strategy.optimal_move, strategy.optimal_rating, num_visited_nodes
