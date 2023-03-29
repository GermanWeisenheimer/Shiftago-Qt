from abc import ABC, abstractmethod
from typing import Optional
import time
import logging
from PyQt5.QtCore import QObject, QThread, pyqtSlot
from shiftago.ui.game_model import ShiftagoExpressModel, PlayerNature
from shiftago.ui.board_view import BoardView, BoardViewEvent, MoveSelectedEvent, AnimationFinishedEvent

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
    def handle_event(self, event: BoardViewEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def leave(self) -> None:
        raise NotImplementedError


class BoardController(QObject):

    class GameOverState(InteractionState):

        def __init__(self, controller: 'BoardController') -> None:
            super().__init__(controller)

        def enter(self):
            game_over_condition = self.controller.model.core_model.game_over_condition
            assert game_over_condition
            self.controller.view.show_game_over(game_over_condition)

        def handle_event(self, event: BoardViewEvent) -> None:
            raise ValueError(f"Unsupported event type: {event.__class__.__name__}")

        def leave(self):
            pass

    class MoveSelectionState(InteractionState):

        def __init__(self, controller: 'BoardController') -> None:
            super().__init__(controller)

        def enter(self):
            self.controller.view.setMouseTracking(True)

        def handle_event(self, event: BoardViewEvent) -> None:
            if event.__class__ == MoveSelectedEvent:
                self._handle_move_selected(event)  # type: ignore
            else:
                raise ValueError(f"Unsupported event type: {event.__class__.__name__}")

        def _handle_move_selected(self, event: MoveSelectedEvent) -> None:
            logger.info(f"Human is making move: {event.move}")
            self._controller.interaction_state = self._controller._performing_animation_state
            self.controller.model.core_model.apply_move(event.move)

        def leave(self):
            self.controller.view.setMouseTracking(False)
            self.controller.view.reset_cursor()

    class ComputerThinkingState(InteractionState):

        class Worker(QObject):

            DELAY = 1.

            def __init__(self, controller: 'BoardController') -> None:
                super().__init__()
                self._controller = controller

            @pyqtSlot()
            def work(self) -> None:
                logger.debug("Thinking...")
                start_time: float = time.time()
                shiftago = self._controller.model.core_model
                move = self._controller.model.ai_engine.select_move(shiftago)
                duration: float = time.time() - start_time
                if duration < self.DELAY:
                    time.sleep(self.DELAY - duration)
                logger.info(f"Computer is making move: {move}")
                self._controller.interaction_state = self._controller._performing_animation_state
                shiftago.apply_move(move)

        def __init__(self, controller: 'BoardController') -> None:
            super().__init__(controller)
            self._thread = QThread()
            self._thread.setObjectName('ThinkingThread')
            self._worker = self.Worker(self.controller)
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.work)  # type: ignore

        def enter(self):
            self._thread.start()

        def handle_event(self, event: BoardViewEvent) -> None:
            raise ValueError(f"Unsupported event type: {event.__class__.__name__}")

        def leave(self) -> None:
            self._thread.quit()

    class PerformingAnimationState(InteractionState):

        def __init__(self, controller: 'BoardController') -> None:
            super().__init__(controller)

        def enter(self):
            pass

        def handle_event(self, event: BoardViewEvent) -> None:
            if event.__class__ == AnimationFinishedEvent:
                current_player_nature = self.controller.model.current_player_nature
                if current_player_nature:
                    if current_player_nature == PlayerNature.HUMAN:
                        self._controller.interaction_state = self._controller.move_selection_state
                    else:
                        self._controller.interaction_state = self._controller.computer_thinking_state
                else:
                    self._controller.interaction_state = self._controller.game_over_state
            else:
                raise ValueError(f"Unsupported event type: {event.__class__}")

        def leave(self):
            logger.debug("Animation finished.")

    def __init__(self, model: ShiftagoExpressModel, view: BoardView) -> None:
        super().__init__()
        self._model = model
        self._view = view
        self._move_selection_state = self.MoveSelectionState(self)
        self._computer_thinking_state = self.ComputerThinkingState(self)
        self._performing_animation_state = self.PerformingAnimationState(self)
        self._game_over_state = self.GameOverState(self)
        view.event_signal.connect(self._on_view_event)  # type: ignore
        self._interaction_state: Optional[InteractionState] = None

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._model

    @property
    def view(self) -> BoardView:
        return self._view

    @property
    def move_selection_state(self) -> MoveSelectionState:
        return self._move_selection_state

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
            self.interaction_state = self._move_selection_state
        else:
            self.interaction_state = self._computer_thinking_state

    @pyqtSlot(BoardViewEvent)
    def _on_view_event(self, event: BoardViewEvent):
        assert self._interaction_state, f"No interaction_state set on BoardController {repr(self)}!"
        self._interaction_state.handle_event(event)
