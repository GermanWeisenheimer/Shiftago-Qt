from abc import ABC, abstractmethod
from typing import Optional, cast
import time
import logging
from PyQt5.QtCore import QObject, QThread, pyqtSlot
from shiftago.ui import Controller, AppEvent, AppEventEmitter
from shiftago.ui.board_view_model import PlayerNature
from shiftago.ui.game_model import ShiftagoExpressModel
from shiftago.ui.board_view import BoardView, MoveSelectedEvent, AnimationFinishedEvent

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

    class GameOverState(InteractionState):

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

    class HumanThinkingState(InteractionState):

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

    class ComputerThinkingState(InteractionState):

        class Worker(AppEventEmitter, QObject):

            DELAY = 1.

            def __init__(self, model: ShiftagoExpressModel) -> None:
                super().__init__()
                self._model = model

            @pyqtSlot()
            def work(self) -> None:
                _logger.debug("Thinking...")
                start_time: float = time.time()
                move = self._model.ai_select_move()
                duration: float = time.time() - start_time
                if duration < self.DELAY:
                    time.sleep(self.DELAY - duration)
                self.emit(MoveSelectedEvent(move))

        def __init__(self, controller: 'BoardController') -> None:
            super().__init__(controller)
            self._thread = QThread()
            self._thread.setObjectName('ThinkingThread')
            self._worker = self.Worker(self.controller.model)
            self.controller.connect_with(self._worker)
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.work)  # type: ignore

        def enter(self):
            self._thread.start()

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
            self._thread.quit()

    class PerformingAnimationState(InteractionState):

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
        self._interaction_states: dict[str, InteractionState] = {
            self.HumanThinkingState.__name__: self.HumanThinkingState(self),
            self.ComputerThinkingState.__name__: self.ComputerThinkingState(self),
            self.PerformingAnimationState.__name__: self.PerformingAnimationState(self),
            self.GameOverState.__name__: self.GameOverState(self)}
        self._active_state: Optional[InteractionState] = None
        self.start_game()

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._model

    @property
    def view(self) -> BoardView:
        return self._view

    @property
    def human_thinking_state(self) -> InteractionState:
        return self._interaction_states[self.HumanThinkingState.__name__]

    @property
    def computer_thinking_state(self) -> InteractionState:
        return self._interaction_states[self.ComputerThinkingState.__name__]

    @property
    def performing_animation_state(self) -> InteractionState:
        return self._interaction_states[self.PerformingAnimationState.__name__]

    @property
    def game_over_state(self) -> InteractionState:
        return self._interaction_states[self.GameOverState.__name__]

    @property
    def active_state(self) -> Optional[InteractionState]:
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
        assert self._active_state, f"No active_state set on BoardController {repr(self)}!"
        return self._active_state.handle_event(event)
