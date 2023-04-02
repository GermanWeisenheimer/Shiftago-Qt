from shiftago.core import Move, GameOverCondition


class AppEvent:

    def __init__(self) -> None:
        pass


class MoveSelectedEvent(AppEvent):

    def __init__(self, move: Move) -> None:
        self._move = move

    def __str__(self) -> str:
        return f"MoveSelectedEvent{self.move}"

    @property
    def move(self) -> Move:
        return self._move


class AnimationFinishedEvent(AppEvent):

    def __init__(self) -> None:
        pass


class ExitRequestedEvent(AppEvent):

    def __init__(self) -> None:
        pass
