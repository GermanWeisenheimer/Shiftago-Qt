from abc import ABC, abstractmethod
from typing import Callable, cast
import time
import logging
from PyQt5.QtCore import QObject, QThread, pyqtSlot
from .hmvc import Controller, AppEvent, AppEventEmitter
from .board_view import BoardView
from .game_model import ShiftagoExpressModel, PlayerNature
from .app_events import MoveSelectedEvent, AnimationFinishedEvent

_logger = logging.getLogger(__name__)


class InteractionState(ABC):

    def __init__(self, controller: 'BoardController') -> None:
        self._controller = controller

    @property
    def controller(self) -> 'BoardController':
        return self._controller

    def __str__(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def enter(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_event(self, event: AppEvent) -> bool:
        raise NotImplementedError

    @abstractmethod
    def leave(self) -> None:
        raise NotImplementedError


class BoardController(Controller):

    class _IdleState(InteractionState):

        def enter(self):
            pass

        def handle_event(self, event: AppEvent) -> bool:
            return False

        def leave(self):
            pass

    class _GameOverState(InteractionState):

        def enter(self):
            game_over_condition = self.controller.model.game_over_condition
            assert game_over_condition
            if game_over_condition.winner:
                _logger.info("Game over: %s has won!", game_over_condition.winner.name)
            else:
                _logger.info("Game over: it has ended in a draw!")
            self.controller.view.show_game_over(game_over_condition)

        def handle_event(self, event: AppEvent) -> bool:
            return False

        def leave(self):
            pass

    class _HumanThinkingState(InteractionState):

        def enter(self):
            self.controller.view.move_selection_enabled = True

        def handle_event(self, event: AppEvent) -> bool:
            if event.__class__ == MoveSelectedEvent:
                self._handle_move_selected(cast(MoveSelectedEvent, event))
                return True
            return False

        def _handle_move_selected(self, event: MoveSelectedEvent) -> None:
            _logger.info("Human is making move: %s", event.move)
            self.controller.active_state = self._controller.performing_animation_state
            self.controller.model.apply_move(event.move)

        def leave(self):
            self.controller.view.move_selection_enabled = False

    class _ComputerThinkingState(InteractionState):

        class Worker(AppEventEmitter, QObject):

            DELAY = 1.

            def __init__(self, model: ShiftagoExpressModel) -> None:
                super().__init__()
                self._model = model
                self._thread = QThread()
                self._thread.setObjectName('ThinkingThread')
                self._thread.started.connect(cast(Callable[[], None], self._work))
                self.moveToThread(self._thread)

            @property
            def thread(self) -> QThread:
                return self._thread

            @pyqtSlot()
            def _work(self) -> None:
                _logger.debug("Thinking...")
                start_time: float = time.time()
                move = self._model.ai_select_move()
                duration: float = time.time() - start_time
                if duration < self.DELAY:
                    time.sleep(self.DELAY - duration)
                self.emit(MoveSelectedEvent(move))

        def __init__(self, controller: 'BoardController') -> None:
            super().__init__(controller)
            self._worker = self.Worker(self.controller.model)
            self.controller.connect_with(self._worker)

        def enter(self):
            self._worker.thread.start()

        def handle_event(self, event: AppEvent) -> bool:
            if event.__class__ == MoveSelectedEvent:
                self._handle_move_selected(cast(MoveSelectedEvent, event))
                return True
            return False

        def _handle_move_selected(self, event: MoveSelectedEvent) -> None:
            _logger.info("Computer is making move: %s", event.move)
            self.controller.active_state = self._controller.performing_animation_state
            self.controller.model.apply_move(event.move)

        def leave(self) -> None:
            self._worker.thread.quit()

    class _PerformingAnimationState(InteractionState):

        def enter(self):
            pass

        def handle_event(self, event: AppEvent) -> bool:
            if event.__class__ == AnimationFinishedEvent:
                current_player_nature = self.controller.model.current_player_nature
                if current_player_nature:
                    if current_player_nature == PlayerNature.HUMAN:
                        self.controller.active_state = self._controller.human_thinking_state
                    else:
                        self.controller.active_state = self._controller.computer_thinking_state
                else:
                    self.controller.active_state = self._controller.game_over_state
                return True
            return False

        def leave(self):
            _logger.debug("Animation finished.")

    def __init__(self, parent: Controller, model: ShiftagoExpressModel, view: BoardView) -> None:
        super().__init__(parent, view)
        self._model = model
        self._view = view
        self._interaction_states: dict[type[InteractionState], InteractionState] = {
            self._IdleState: self._IdleState(self),
            self._HumanThinkingState: self._HumanThinkingState(self),
            self._ComputerThinkingState: self._ComputerThinkingState(self),
            self._PerformingAnimationState: self._PerformingAnimationState(self),
            self._GameOverState: self._GameOverState(self)}
        self._active_state: InteractionState = self.idle_state

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._model

    @property
    def view(self) -> BoardView:
        return self._view

    @property
    def idle_state(self) -> InteractionState:
        return self._interaction_states[self._IdleState]

    @property
    def human_thinking_state(self) -> InteractionState:
        return self._interaction_states[self._HumanThinkingState]

    @property
    def computer_thinking_state(self) -> InteractionState:
        return self._interaction_states[self._ComputerThinkingState]

    @property
    def performing_animation_state(self) -> InteractionState:
        return self._interaction_states[self._PerformingAnimationState]

    @property
    def game_over_state(self) -> InteractionState:
        return self._interaction_states[self._GameOverState]

    @property
    def active_state(self) -> InteractionState:
        return self._active_state

    @active_state.setter
    def active_state(self, new_state: InteractionState) -> None:
        if self._active_state:
            _logger.debug("Leaving state %s.", self._active_state)
            self._active_state.leave()
        self._active_state = new_state
        _logger.debug("Entering state %s.", self._active_state)
        self._active_state.enter()

    def start_game(self) -> None:
        assert self.model.current_player, "No current player!"
        if self.model.current_player_nature == PlayerNature.HUMAN:
            self.active_state = self.human_thinking_state
        else:
            self.active_state = self.computer_thinking_state

    def handle_event(self, event: AppEvent) -> bool:
        return self._active_state.handle_event(event)
