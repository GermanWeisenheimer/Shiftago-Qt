# pylint: disable=no-name-in-module
from abc import ABC, abstractmethod
from typing import Optional
import time
import logging
from PyQt5.QtCore import QObject, QThread, pyqtSlot
from shiftago.ui.hmvc import Controller, AppEventEmitter
from shiftago.ui.app_events import AppEvent
from shiftago.ui.game_model import ShiftagoExpressModel, PlayerNature
from shiftago.ui.board_view import BoardView, MoveSelectedEvent, AnimationFinishedEvent

logger = logging.getLogger(__name__)


class InteractionState(ABC):

    def __init__(self, controller: 'BoardController') -> None:
        self._controller = controller

    @property
    def controller(self) -> 'BoardController':
        return self._controller

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
                logger.info(f"Game over: {game_over_condition.winner.name} has won!")
            else:
                logger.info("Game over: it has ended in a draw!")
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
                self._handle_move_selected(event)  # type: ignore
                return True
            return False

        def _handle_move_selected(self, event: MoveSelectedEvent) -> None:
            logger.info(f"Human is making move: {event.move}")
            self.controller.interaction_state = self._controller._performing_animation_state
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
                logger.debug("Thinking...")
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
                self._handle_move_selected(event)  # type: ignore
                return True
            return False

        def _handle_move_selected(self, event: MoveSelectedEvent) -> None:
            logger.info(f"Computer is making move: {event.move}")
            self.controller.interaction_state = self._controller._performing_animation_state
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
                        self.controller.interaction_state = self._controller.human_thinking_state
                    else:
                        self.controller.interaction_state = self._controller.computer_thinking_state
                else:
                    self.controller.interaction_state = self._controller.game_over_state
                return True
            return False

        def leave(self):
            logger.debug("Animation finished.")

    def __init__(self, parent: Controller, model: ShiftagoExpressModel, view: BoardView) -> None:
        super().__init__(parent, view)
        self._model = model
        self._view = view
        self._human_thinking_state = self.HumanThinkingState(self)
        self._computer_thinking_state = self.ComputerThinkingState(self)
        self._performing_animation_state = self.PerformingAnimationState(self)
        self._game_over_state = self.GameOverState(self)
        self._interaction_state: Optional[InteractionState] = None
        self.start_game()

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._model

    @property
    def view(self) -> BoardView:
        return self._view

    @property
    def human_thinking_state(self) -> HumanThinkingState:
        return self._human_thinking_state

    @property
    def computer_thinking_state(self) -> ComputerThinkingState:
        return self._computer_thinking_state

    @property
    def game_over_state(self) -> GameOverState:
        return self._game_over_state

    @property
    def interaction_state(self) -> Optional[InteractionState]:
        return self._interaction_state

    @interaction_state.setter
    def interaction_state(self, new_state: InteractionState) -> None:
        if self._interaction_state:
            logger.debug(f"Leaving state {self._interaction_state.__class__.__name__}.")
            self._interaction_state.leave()
        self._interaction_state = new_state
        logger.debug(f"Entering state {self._interaction_state.__class__.__name__}.")
        self._interaction_state.enter()

    def start_game(self) -> None:
        assert self.model.current_player, "No current player!"
        if self.model.current_player_nature == PlayerNature.HUMAN:
            self.interaction_state = self._human_thinking_state
        else:
            self.interaction_state = self._computer_thinking_state

    def handle_event(self, event: AppEvent) -> bool:
        assert self._interaction_state, f"No interaction_state set on BoardController {repr(self)}!"
        return self._interaction_state.handle_event(event)
