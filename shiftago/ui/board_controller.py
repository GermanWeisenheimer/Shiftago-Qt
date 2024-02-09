import time
import logging
from functools import singledispatchmethod
from PySide2.QtCore import QObject, QThread
from statemachine import StateMachine, State
from shiftago.ui import Controller, AppEvent, AppEventEmitter
from .board_view import BoardView
from .game_model import ShiftagoExpressModel, PlayerNature
from .app_events import ReadyForFirstMoveEvent, MoveSelectedEvent, AnimationFinishedEvent

_logger = logging.getLogger(__name__)


class BoardController(Controller):

    class _BoardStateMaschine(AppEventEmitter, StateMachine):

        start_player_notification_state = State('StartPlayerNotification', initial=True)
        computer_thinking_state = State('ComputerThinking')
        human_thinking_state = State('HumanThinking')
        performing_animation_state = State('PerformingAnimation')
        game_over_state = State('GameOver', final=True)

        to_animation = computer_thinking_state.to(performing_animation_state) | \
            human_thinking_state.to(performing_animation_state)
        to_artifial_player = start_player_notification_state.to(computer_thinking_state) | \
            performing_animation_state.to(computer_thinking_state)
        to_human_player = start_player_notification_state.to(human_thinking_state) | \
            performing_animation_state.to(human_thinking_state)
        to_end_of_game = performing_animation_state.to(game_over_state)

        class ComputerThinkingWorker(QObject):

            DELAY = 1.

            def __init__(self, model: ShiftagoExpressModel,
                         app_event_emitter: AppEventEmitter) -> None:
                super().__init__()
                self._model = model
                self._app_event_emitter = app_event_emitter
                self._thread = QThread()
                self._thread.setObjectName('ThinkingThread')
                self.moveToThread(self._thread)
                self._thread.started.connect(self._think)

            def _think(self) -> None:
                _logger.debug("Computer is thinking...")
                start_time: float = time.time()
                move = self._model.ai_select_move()
                duration: float = time.time() - start_time
                if duration < self.DELAY:
                    time.sleep(self.DELAY - duration)
                self._app_event_emitter.emit(MoveSelectedEvent(move))

        def __init__(self, model: ShiftagoExpressModel, view: BoardView) -> None:
            super().__init__()
            self._model = model
            self._view = view
            self._computer_thinking_worker = self.ComputerThinkingWorker(model, self)

        @computer_thinking_state.enter
        def enter_computer_thinking(self) -> None:
            self._computer_thinking_worker.thread().start()

        @computer_thinking_state.exit
        def exit_computer_thinking(self) -> None:
            self._computer_thinking_worker.thread().quit()

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

    @model.setter
    def model(self, new_model: ShiftagoExpressModel) -> None:
        self._model = new_model
        self._state_machine = self._BoardStateMaschine(new_model, self._view)
        self.connect_with(self._state_machine)

    @property
    def view(self) -> BoardView:
        return self._view

    def start_match(self) -> None:
        self._view.show_starting_player()

    @singledispatchmethod
    def handle_event(self, _: AppEvent) -> bool:
        return False

    @handle_event.register
    def _(self, _: ReadyForFirstMoveEvent) -> bool:  # pylint: disable=unused-argument
        current_player = self._model.current_player
        _logger.info("Starting player is %s (%s).", current_player.colour.name,
                     'human' if current_player.nature is PlayerNature.HUMAN else 'computer')
        _logger.info("Skill level: %s", self._model.skill_level.name)
        if current_player.nature is PlayerNature.HUMAN:
            self._state_machine.to_human_player()
        else:
            self._state_machine.to_artifial_player()
        return True

    @handle_event.register
    def _(self, event: MoveSelectedEvent) -> bool:
        assert self._state_machine.current_state in (self._BoardStateMaschine.computer_thinking_state,
                                                     self._BoardStateMaschine.human_thinking_state)
        current_player = self._model.current_player
        if current_player.nature is PlayerNature.HUMAN:
            _logger.info("Human is making move: %s", event.move)
        else:
            _logger.info("Computer is making move: %s", event.move)
        self._state_machine.to_animation()
        self._model.apply_move(event.move)
        return True

    @handle_event.register
    def _(self, _: AnimationFinishedEvent) -> bool:  # pylint: disable=unused-argument
        assert self._state_machine.current_state == self._BoardStateMaschine.performing_animation_state
        _logger.debug("Animation finished.")
        if self._model.game_over_condition is None:
            if self._model.current_player.nature is PlayerNature.HUMAN:
                self._state_machine.to_human_player()
            else:
                self._state_machine.to_artifial_player()
        else:
            self._state_machine.to_end_of_game()
        return True
