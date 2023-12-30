from enum import Enum
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from shiftago.core import Shiftago, Move


class SkillLevel(Enum):
    ROOKIE = 0
    ADVANCED = 1
    EXPERT = 2


S = TypeVar("S", bound=Shiftago)


class AIEngine(ABC, Generic[S]):

    def __init__(self, skill_level: SkillLevel) -> None:
        self._skill_level = skill_level

    @property
    def skill_level(self) -> SkillLevel:
        return self._skill_level

    @abstractmethod
    def select_move(self, game_state: S) -> Move:
        raise NotImplementedError
