# pylint: disable=consider-using-f-string
import logging
import math
import random
import copy
from collections import defaultdict, namedtuple
from typing import List, Tuple, Optional, Sequence, Dict
from abc import ABC, abstractmethod
from functools import lru_cache
from shiftago.core import AIEngine, SkillLevel
from .express import ShiftagoExpress, Move, GameOverCondition

_logger = logging.getLogger(__name__)


def analyze_colour_placements(game_state: ShiftagoExpress) -> Sequence[Dict[int, int]]:
    """
    Analyzes the placement of colors on the game board and detects potential winning lines for each player.
    
    Parameters:
    game_state: The current state of the game.
    
    Returns:
    A sequence of dictionaries where each dictionary corresponds to a player and maps 
    match group indices to the number of times they appear in potential winning lines.
    """
    # Detect winning lines for each player
    winning_line_matches = game_state.detect_winning_lines(2)
    results = tuple(defaultdict(lambda: 0) for _ in winning_line_matches)  # type: Sequence[Dict[int, int]]
    for player_idx, match_groups_of_player in enumerate(results):
        for match_group_index in winning_line_matches[player_idx].values():
            match_groups_of_player[match_group_index] = match_groups_of_player[match_group_index] + 1
    return results


class _Rating(namedtuple('Rating', 'value depth')):
    """
    _Rating is a named tuple that represents the evaluation of a game state in the 
    Alpha-Beta pruning algorithm. It contains the rating value and the depth at which 
    the rating was determined.
    
    Attributes:
    value (float): The evaluation score of the game state.
    depth (int): The depth in the game tree at which the rating was determined.
    """


class _Node:
    """
    _Node represents a node in the game tree for the Alpha-Beta pruning algorithm. 
    Each node corresponds to a game state resulting from a specific move. 
    It stores the move that led to this game state, the resulting game state, 
    and whether the game is over after this move.
    """

    def __init__(self, from_game_state: ShiftagoExpress, move: Move) -> None:
        self._move = move
        self._target_game_state = copy.copy(from_game_state)
        self._game_over_condition = self._target_game_state.apply_move(move)

    def __str__(self) -> str:
        return "(move: {0}, is_leaf: {1})".format(self._move, self.is_leaf)

    def __hash__(self) -> int:
        return hash(self._move)

    @property
    def move(self) -> Move:
        """
        Returns the move that led to this game state.
        """
        return self._move

    @property
    def target_game_state(self) -> ShiftagoExpress:
        """
        Returns the resulting game state after applying the move.
        """
        return self._target_game_state

    @property
    def game_over_condition(self) -> Optional[GameOverCondition]:
        """
        Indicates whether the game is over after this move. If the game is not over,
        this property will be None.
        """
        return self._game_over_condition

    @property
    def is_leaf(self) -> bool:
        """
        Indicates whether this node is a leaf node in the game tree.
        """
        return self._game_over_condition is not None


class _MiniMaxStrategy(ABC):
    """
    _MiniMaxStrategy is an abstract base class for implementing the minimax strategy 
    with Alpha-Beta pruning. It defines common properties and methods used by both 
    maximizing and minimizing strategies in the game tree search.
    """

    def __init__(self, alpha_beta: Tuple[float, float]) -> None:
        self._alpha, self._beta = alpha_beta
        if self.is_maximizing:
            self._win_rating_value = 1
        else:
            self._win_rating_value = -1
        self._optimal_rating = None  # type: Optional[_Rating]

    @property
    def alpha_beta(self) -> Tuple[float, float]:
        """
        Returns the current alpha and beta values for pruning.
        """
        return self._alpha, self._beta

    @property
    def optimal_rating(self) -> _Rating:
        """
        Returns the optimal rating found during the search.
        """
        assert self._optimal_rating is not None
        return self._optimal_rating

    @property
    @abstractmethod
    def is_maximizing(self) -> bool:
        """
        Abstract property that indicates whether the current strategy is maximizing or minimizing.
        This property should be implemented by subclasses to return True if the strategy is 
        maximizing, and False if the strategy is minimizing.

        Returns:
        True if the strategy is maximizing, False if it is minimizing.
        """

    def sort_nodes(self, nodes: List) -> None:
        """
        Sorts the given list of nodes based on their evaluation scores. The nodes are sorted 
        in descending order if the current strategy is maximizing, and in ascending order if 
        the strategy is minimizing. This pre-sorting helps improve the efficiency of the 
        Alpha-Beta pruning algorithm by increasing the likelihood of pruning suboptimal branches early.
        """
        ratings = {node: self.evaluate(node) for node in nodes}
        nodes.sort(key=lambda n: ratings[n], reverse=self.is_maximizing)

    def evaluate(self, node: _Node) -> float:
        """
        Evaluates the given node in the game tree and returns a rating value based on the current game state.
        """
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
        """
        Determines whether the current branch of the game tree can be pruned based on the 
        alpha and beta values. Pruning occurs when the alpha value is greater than or equal 
        to the beta value, indicating that further exploration of this branch will not yield 
        a better result.
        
        Returns:
        True if the branch can be pruned, False otherwise.
        """
        return self._alpha >= self._beta

    @abstractmethod
    def check_optimal(self, rating: _Rating) -> bool:
        """
        Abstract method to check if the given rating is optimal based on the current strategy 
        (maximizing or minimizing). This method should be implemented by subclasses to update 
        the optimal rating and determine if the current rating is better than the previously 
        found optimal rating.
        
        Parameters:
        rating: The rating to be checked.
        
        Returns:
        True if the rating is optimal, False otherwise.
        """

class AlphaBetaPruning(AIEngine[ShiftagoExpress]):
    """
    AlphaBetaPruning is an implementation of the Alpha-Beta pruning algorithm, 
    which is an optimization technique for the minimax algorithm. It reduces 
    the number of nodes evaluated in the search tree by eliminating branches 
    that cannot possibly influence the final decision. This class contains 
    nested classes and methods to handle the maximizing and minimizing strategies 
    during the search process.
    """

    class _Maximizer(_MiniMaxStrategy):
        """
        _Maximizer is a concrete implementation of the _MiniMaxStrategy abstract base class 
        for the maximizing strategy in the Alpha-Beta pruning algorithm. This strategy aims 
        to maximize the evaluation score, representing the AI's best move.
        """

        @property
        def is_maximizing(self) -> bool:
            """
            Indicates that this strategy is maximizing.
            
            Returns:
            True, as this strategy is maximizing.
            """
            return True

        def check_optimal(self, rating: _Rating) -> bool:
            """
            Checks if the given rating is optimal based on the maximizing strategy. Updates 
            the optimal rating if the current rating is better than the previously found 
            optimal rating.
            
            Parameters:
            rating: The rating to be checked.
            
            Returns:
            True if the rating is optimal, False otherwise.
            """
            if self._optimal_rating is None or rating.value > self._optimal_rating.value:
                self._optimal_rating = rating
                self._alpha = max(self._alpha, self._optimal_rating.value)
                return True
            if rating.value == self._optimal_rating.value:
                if rating.depth < self._optimal_rating.depth if rating.value > 0. else \
                        rating.depth > self._optimal_rating.depth:
                    self._optimal_rating = rating
                    return True
            return False

    class _Minimizer(_MiniMaxStrategy):
        """
        _Minimizer is a concrete implementation of the _MiniMaxStrategy abstract base class 
        for the minimizing strategy in the Alpha-Beta pruning algorithm. This strategy aims 
        to minimize the evaluation score, representing the opponent's best move.
        """

        @property
        def is_maximizing(self) -> bool:
            """
            Indicates that this strategy is minimizing.
            
            Returns:
            False, as this strategy is minimizing.
            """
            return False

        def check_optimal(self, rating: _Rating) -> bool:
            """
            Checks if the given rating is optimal based on the minimizing strategy. Updates 
            the optimal rating if the current rating is better than the previously found 
            optimal rating.
            
            Parameters:
            rating: The rating to be checked.
            
            Returns:
            True if the rating is optimal, False otherwise.
            """
            if self._optimal_rating is None or rating.value < self._optimal_rating.value:
                self._optimal_rating = rating
                self._beta = min(self._beta, self._optimal_rating.value)
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
        """
        Selects the best move for the AI based on the current game state using the Alpha-Beta pruning algorithm.
        
        Parameters:
        game_state (ShiftagoExpress): The current state of the game.
        
        Returns:
        The selected move.
        """
        # Ensure the game involves exactly two players
        assert len(game_state.colours) == 2

        # If more than one slot is occupied, use the Alpha-Beta pruning algorithm to select the move
        if game_state.count_occupied_slots() > 1:
            move, rating = self._apply(game_state, 1, (-math.inf, math.inf))
            _logger.debug("Selected move: %s (%s)", move, rating)
            return move

        # If only one slot is occupied, select a random move from all possible moves
        move = random.choice(game_state.detect_all_possible_moves())
        _logger.debug("Selected random move: %s", move)
        return move

    def _apply(self, game_state: ShiftagoExpress, depth: int, alpha_beta: Tuple[float, float]) \
            -> Tuple[Move, _Rating]:
        """
        Recursively applies the Alpha-Beta pruning algorithm to evaluate and select the optimal move.
        
        Parameters:
        game_state: The current state of the game.
        depth: The current depth in the game tree.
        alpha_beta: The current alpha and beta values for pruning.
        
        Returns:
        The optimal move and its corresponding rating.
        """
        strategy = self._Maximizer(alpha_beta) if depth % 2 == 1 else self._Minimizer(alpha_beta)
        nodes = [_Node(game_state, move) for move in game_state.detect_all_possible_moves()]
        if depth < self._max_depth:
            # Pre-sorting massively increases the efficiency of pruning!
            strategy.sort_nodes(nodes)
        optimal_move = None
        for each_node in nodes:
            if each_node.is_leaf or depth == self._max_depth:
                current_rating = _Rating(strategy.evaluate(each_node), depth)
            else:
                _, current_rating = self._apply(each_node.target_game_state, depth + 1, strategy.alpha_beta)
            if strategy.check_optimal(current_rating):
                optimal_move = each_node.move
                if strategy.can_prune():
                    break
        assert optimal_move is not None
        return optimal_move, strategy.optimal_rating
