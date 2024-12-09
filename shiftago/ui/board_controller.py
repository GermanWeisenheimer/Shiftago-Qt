import time
import logging
from functools import singledispatchmethod
from PySide6.QtCore import QObject, QThread
from statemachine import StateMachine, State
from shiftago.ui import Controller, AppEvent, AppEventEmitter
from .board_view import BoardView
from .game_model import ShiftagoExpressModel, PlayerNature
from .app_events import ReadyForFirstMoveEvent, MoveSelectedEvent, AnimationFinishedEvent

_logger = logging.getLogger(__name__)


class BoardController(Controller):
    """
    BoardController is responsible for managing the interactions between the game model and the view.
    It handles user input, updates the game state, and triggers animations and events based on the game logic.
    """

    class _BoardStateMachine(AppEventEmitter, StateMachine):
        """
        _BoardStateMachine is a state machine that manages the different states of the game board.
        It handles transitions between states such as player notification, computer thinking, human thinking,
        performing animations, and game over.
        """

        # States of the game board
        start_player_notification_state = State('StartPlayerNotification', initial=True)
        computer_thinking_state = State('ComputerThinking')
        human_thinking_state = State('HumanThinking')
        performing_animation_state = State('PerformingAnimation')
        game_over_state = State('GameOver', final=True)

        # Transitions between states
        to_animation = computer_thinking_state.to(performing_animation_state) | \
            human_thinking_state.to(performing_animation_state)
        to_artifial_player = start_player_notification_state.to(computer_thinking_state) | \
            performing_animation_state.to(computer_thinking_state)
        to_human_player = start_player_notification_state.to(human_thinking_state) | \
            performing_animation_state.to(human_thinking_state)
        to_end_of_game = performing_animation_state.to(game_over_state)

        class ComputerThinkingWorker(QObject):
            """
            ComputerThinkingWorker is responsible for handling the AI's thinking process in a separate thread.
            It performs the AI's move calculation and emits events when the AI has selected a move.

            Attributes:
            DELAY (float): The delay in seconds before the AI makes a move.
            """

            DELAY = 1.

            def __init__(self, model: ShiftagoExpressModel,
                         app_event_emitter: AppEventEmitter) -> None:
                """
                Initializes the ComputerThinkingWorker with the given model and event emitter.
                """
                super().__init__()
                self._model = model
                self._app_event_emitter = app_event_emitter
                self._thread = QThread()
                self._thread.setObjectName('ThinkingThread')
                self.moveToThread(self._thread)
                self._thread.started.connect(self._think)

            def _think(self) -> None:
                """
                Performs the AI's move calculation and emits an event when the move is selected.
                """
                _logger.debug("Computer is thinking...")
                start_time: float = time.time()
                move = self._model.ai_select_move()
                duration: float = time.time() - start_time
                if duration < self.DELAY:
                    time.sleep(self.DELAY - duration)
                self._app_event_emitter.emit(MoveSelectedEvent(move))

        def __init__(self, model: ShiftagoExpressModel, view: BoardView) -> None:
            """
            Initializes the _BoardStateMachine with the given model and view.
            """
            super().__init__()
            self._model = model
            self._view = view
            self._computer_thinking_worker = self.ComputerThinkingWorker(model, self)

        @computer_thinking_state.enter
        def enter_computer_thinking(self) -> None:
            """
            On entering the computer thinking state the computer thinking worker thread is started.
            """
            self._computer_thinking_worker.thread().start()

        @computer_thinking_state.exit
        def exit_computer_thinking(self) -> None:
            """
            On exiting the computer thinking state the computer thinking worker thread is stopped.
            """
            self._computer_thinking_worker.thread().quit()

        @human_thinking_state.enter
        def enter_human_thinking(self) -> None:
            """
            On entering the human thinking state move selection by mouse is enabled.
            """
            self._view.move_selection_enabled = True

        @human_thinking_state.exit
        def exit_human_thinking(self) -> None:
            """
            On exiting the human thinking state move selection by mouse is disabled.
            """
            self._view.move_selection_enabled = False

        @game_over_state.enter
        def enter_game_over(self) -> None:
            """
            On entering the game over state the user is informed about the winner
            and the winning line(s).
            """
            game_over_condition = self._model.game_over_condition
            assert game_over_condition is not None
            if game_over_condition.winner:
                _logger.info("Game over: %s has won!", game_over_condition.winner.name)
                self._view.mark_lines(self._model.winning_lines_of_winner())
            else:
                _logger.info("Game over: it has ended in a draw!")
            self._view.show_game_over()

    def __init__(self, parent: Controller, model: ShiftagoExpressModel, view: BoardView) -> None:
        """
        Initializes the BoardController with the given parent controller, model and view.
        """
        super().__init__(parent, view)
        self._model = model
        self._view = view
        self._init_state_machine()

    def _init_state_machine(self) -> None:
        """
        Initializes the state machine for the game board.
        """
        self._state_machine = self._BoardStateMachine(self._model, self._view)
        self.connect_with(self._state_machine)

    def reset(self) -> None:
        """
        Resets the game model and reinitializes the state machine.
        """
        self._model.reset()
        self._init_state_machine()

    @property
    def model(self) -> ShiftagoExpressModel:
        """
        Returns the game model.
        """
        return self._model

    @property
    def view(self) -> BoardView:
        """
        Returns the view the controller is responsible for.
        """
        return self._view

    def start_game(self) -> None:
        """
        Start game by informing the user about the starting player.
        """
        self._view.show_starting_player()

    @singledispatchmethod
    def handle_event(self, _: AppEvent) -> bool:
        """
        Handles application events. This method is a single-dispatch method that can be extended
        to handle different types of events.

        Returns:
        True if the event was handled, False otherwise.
        """
        return False

    @handle_event.register
    def _(self, _: ReadyForFirstMoveEvent) -> bool:
        """
        Handles the ReadyForFirstMoveEvent. Determines the starting player and transitions to the appropriate state.
        """
        current_player = self._model.whose_turn_it_is
        _logger.info("Starting player is %s (%s).", current_player.colour.name,
                     'human' if current_player.nature is PlayerNature.HUMAN else 'computer')
        _logger.info("Skill level: %s", self._model.skill_level.name)
        if current_player.nature is PlayerNature.HUMAN:
            self._state_machine.to_human_player()  # type: ignore
        else:
            self._state_machine.to_artifial_player()  # type: ignore
        return True

    @handle_event.register
    def _(self, event: MoveSelectedEvent) -> bool:
        """
        Handles the MoveSelectedEvent. Applies the move and transitions to the animation state.
        """
        assert self._state_machine.current_state in (self._BoardStateMachine.computer_thinking_state,
                                                     self._BoardStateMachine.human_thinking_state)
        current_player = self._model.whose_turn_it_is
        if current_player.nature is PlayerNature.HUMAN:
            _logger.info("Human is making move: %s", event.move)
        else:
            _logger.info("Computer is making move: %s", event.move)
        self._state_machine.to_animation()  # type: ignore
        self._model.apply_move(event.move)
        return True

    @handle_event.register
    def _(self, _: AnimationFinishedEvent) -> bool:
        """
        Handles the AnimationFinishedEvent. Determines the next state based on the game state.
        """
        assert self._state_machine.current_state == self._BoardStateMachine.performing_animation_state
        _logger.debug("Animation finished.")
        if self._model.game_over_condition is None:
            if self._model.whose_turn_it_is.nature is PlayerNature.HUMAN:
                self._state_machine.to_human_player()  # type: ignore
            else:
                self._state_machine.to_artifial_player()  # type: ignore
        else:
            self._state_machine.to_end_of_game()  # type: ignore
        return True
