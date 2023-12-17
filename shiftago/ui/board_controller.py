from typing import Callable, cast
import time
import logging
from PyQt5.QtCore import QObject, QThread, pyqtSlot
from statemachine import StateMachine, State
from .hmvc import Controller, AppEvent, AppEventEmitter
from .board_view import BoardView
from .game_model import ShiftagoExpressModel, PlayerNature
from .app_events import MoveSelectedEvent, AnimationFinishedEvent

_logger = logging.getLogger(__name__)


class BoardController(Controller):

    class _BoardStateMaschine(AppEventEmitter, StateMachine):

        class ComputerThinkingWorker(QObject):

            DELAY = 1.

            def __init__(self, model: ShiftagoExpressModel, app_event_emitter: AppEventEmitter) -> None:
                super().__init__()
                self._model = model
                self._app_event_emitter = app_event_emitter
                self._thread = QThread()
                self._thread.setObjectName('ThinkingThread')
                self._thread.started.connect(cast(Callable[[], None], self._work))
                self.moveToThread(self._thread)

            @property
            def thread(self) -> QThread:
                return self._thread

            @pyqtSlot()
            def _work(self) -> None:
                _logger.debug("Computer is thinking...")
                start_time: float = time.time()
                move = self._model.ai_select_move()
                duration: float = time.time() - start_time
                if duration < self.DELAY:
                    time.sleep(self.DELAY - duration)
                self._app_event_emitter.emit(MoveSelectedEvent(move))

            def start_work(self):
                self._thread.start()

            def finish_work(self):
                self._thread.quit()

        idle_state = State('Idle', initial=True)
        computer_thinking_state = State('ComputerThinking')
        human_thinking_state = State('HumanThinking')
        performing_animation_state = State('PerformingAnimation')
        game_over_state = State('GameOver', final=True)

        start_game = idle_state.to(human_thinking_state)
        perform_animation = computer_thinking_state.to(performing_animation_state) | \
            human_thinking_state.to(performing_animation_state)
        computer_on_turn = performing_animation_state.to(computer_thinking_state)
        human_on_turn = performing_animation_state.to(human_thinking_state)
        finish_game = performing_animation_state.to(game_over_state)

        def __init__(self, model: ShiftagoExpressModel, view: BoardView) -> None:
            super().__init__()
            self._model = model
            self._view = view
            self._computer_thinking_worker = self.ComputerThinkingWorker(model, self)

        @computer_thinking_state.enter
        def enter_computer_thinking(self) -> None:
            self._computer_thinking_worker.start_work()

        @computer_thinking_state.exit
        def exit_computer_thinking(self) -> None:
            self._computer_thinking_worker.finish_work()

        @human_thinking_state.enter
        def enter_human_thinking(self) -> None:
            self._view.move_selection_enabled = True

        @human_thinking_state.exit
        def exit_human_thinking(self) -> None:
            self._view.move_selection_enabled = False

        @game_over_state.enter
        def enter_game_over(self) -> None:
            game_over_condition = self._model.game_over_condition
            assert game_over_condition is not None
            if game_over_condition.winner:
                _logger.info("Game over: %s has won!", game_over_condition.winner.name)
            else:
                _logger.info("Game over: it has ended in a draw!")
            self._view.show_game_over()

    def __init__(self, parent: Controller, model: ShiftagoExpressModel, view: BoardView) -> None:
        super().__init__(parent, view)
        self._model = model
        self._view = view
        self._state_machine = self._BoardStateMaschine(model, view)
        self.connect_with(self._state_machine)

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._model

    @property
    def view(self) -> BoardView:
        return self._view

    def start_game(self) -> None:
        assert self.model.current_player is not None, "No current player!"
        self._state_machine.send('start_game')

    def handle_event(self, event: AppEvent) -> bool:
        if event.__class__ == MoveSelectedEvent:
            assert self._state_machine.current_state in (self._BoardStateMaschine.computer_thinking_state,
                                                         self._BoardStateMaschine.human_thinking_state)
            self._handle_move_selected(cast(MoveSelectedEvent, event))
            return True
        if event.__class__ == AnimationFinishedEvent:
            assert self._state_machine.current_state == self._BoardStateMaschine.performing_animation_state
            self._handle_animation_finished()
            return True
        return False

    def _handle_move_selected(self, event: MoveSelectedEvent) -> None:
        if self._model.current_player_nature == PlayerNature.HUMAN:
            _logger.info("Human is making move: %s", event.move)
        else:
            _logger.info("Computer is making move: %s", event.move)
        self._state_machine.send('perform_animation')
        self._model.apply_move(event.move)

    def _handle_animation_finished(self) -> None:
        _logger.debug("Animation finished.")
        current_player_nature = self.model.current_player_nature
        if current_player_nature is not None:
            event = 'human_on_turn' if current_player_nature == PlayerNature.HUMAN else 'computer_on_turn'
        else:
            event = 'finish_game'
        self._state_machine.send(event)
