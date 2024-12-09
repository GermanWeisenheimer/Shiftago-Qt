import logging
import os
from datetime import datetime
from importlib.metadata import version
from functools import singledispatchmethod
from typing import override
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog
from PySide6.QtGui import QIcon, QAction, QCloseEvent
from shiftago.app_config import ShiftagoConfig
from shiftago.core import Colour
from shiftago.ui import load_image, Controller, AppEvent, AppEventEmitter
from .board_view import BoardView, BOARD_VIEW_SIZE
from .app_events import NewGameRequestedEvent, ScreenshotRequestedEvent, AppInfoRequestedEvent, ExitRequestedEvent
from .game_model import ShiftagoExpressModel, PlayerNature, Player
from .board_controller import BoardController

_logger = logging.getLogger(__name__)


def _build_model(config: ShiftagoConfig) -> ShiftagoExpressModel:
    humans_colour = config.preferred_colour
    computers_colour = Colour.ORANGE if humans_colour is Colour.BLUE else Colour.BLUE
    return ShiftagoExpressModel((Player(humans_colour, PlayerNature.HUMAN),
                                 Player(computers_colour, PlayerNature.ARTIFICIAL)), config)


class _MainWindow(AppEventEmitter, QMainWindow):
    """
    _MainWindow is the main window of the Shiftago-Qt application.
    It initializes the game model, sets up the user interface, and handles user interactions.
    """

    TITLE = 'Shiftago-Qt'

    def __init__(self, config: ShiftagoConfig):
        """
        Initializes the _MainWindow with the given configuration.
        """
        super().__init__()
        self._model = _build_model(config)
        self.setWindowTitle(self.TITLE)
        self.setStyleSheet("background-color: lightGray;")
        self.setFixedSize(QSize(BOARD_VIEW_SIZE.width() + 28, BOARD_VIEW_SIZE.height() + 35))
        self._board_view = BoardView(self._model, self.TITLE)
        self.setCentralWidget(self._board_view)
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('About', lambda: self.emit(AppInfoRequestedEvent()))
        file_menu.addAction('New game', lambda: self.emit(NewGameRequestedEvent()))

        screenshot_action = QAction(QIcon(load_image('screenshot-icon.png')), '&Screenshot', self)
        screenshot_action.triggered.connect(lambda: self.emit(ScreenshotRequestedEvent()))
        file_menu.addAction(screenshot_action)

        exit_action = QAction(QIcon(load_image('exit-icon.png')), '&Exit', self)
        exit_action.triggered.connect(lambda: self.emit(ExitRequestedEvent()))
        file_menu.addAction(exit_action)

        self._exit_confirmed = False

    @override
    def closeEvent(self, event: QCloseEvent):  # pylint: disable=invalid-name
        """
        Handles the close event of the main window. Emits an ExitRequestedEvent if the exit is not confirmed.
        """
        if not self._exit_confirmed:
            event.ignore()
            self.emit(ExitRequestedEvent())

    def confirm_abort(self) -> bool:
        """
        Displays a confirmation dialog to confirm aborting the current game.
        Returns True if the user confirms the abort, False otherwise.
        """
        reply = QMessageBox.question(self, self.TITLE, 'Are you sure you want to abort the current game?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    def confirm_exit(self) -> bool:
        """
        Displays a confirmation dialog to confirm exiting the application.
        Returns True if the user confirms the exit, False otherwise.
        """
        reply = QMessageBox.question(self, self.TITLE, 'Are you sure you want to quit?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._exit_confirmed = True
        return self._exit_confirmed

    def set_exit_confirmed(self, confirmed: bool) -> None:
        """
        Sets the 'exit confirmed' flag.
        """
        self._exit_confirmed = confirmed

    @property
    def board_view(self) -> BoardView:
        """
        Returns the BoardView child of the main window.
        """
        return self._board_view

    @property
    def model(self) -> ShiftagoExpressModel:
        """
        Returns the game model associated with the main window.
        """
        return self._model


class _MainWindowController(Controller):
    """
    _MainWindowController is responsible for managing the interactions between the main window and the game logic.
    It initializes the main window, sets up the board controller, and handles application events.
    """

    def __init__(self, config: ShiftagoConfig, main_window: _MainWindow) -> None:
        """
        Initializes the _MainWindowController with the given configuration and main window.
        """
        super().__init__(None, main_window)
        self._config = config
        self._board_controller = BoardController(self, main_window.model, main_window.board_view)
        self._main_window = main_window
        self._main_window.show()
        self._board_controller.start_match()

    @property
    def model(self) -> ShiftagoExpressModel:
        """
        Returns the game model associated with the main window controller.
        """
        return self._main_window.model

    @singledispatchmethod
    def handle_event(self, _: AppEvent) -> bool:
        """
        Handles application events. This method is a single-dispatch method that can be extended
        to handle different types of events.

        Parameters:
        _: AppEvent: The event to be handled.

        Returns:
        True if the event has been handled, False otherwise.
        """
        return False

    @handle_event.register
    def _(self, _: AppInfoRequestedEvent) -> bool:
        """
        Handles the AppInfoRequestEvent. Open information dialog showing version and copyright.
        """
        QMessageBox.information(self._main_window, self._main_window.TITLE,
                                f"Shiftago-Qt v{version('shiftago-qt')}\n\u00A9 2024 Thomas Schaper",
                                QMessageBox.StandardButton.Ok)
        return True

    @handle_event.register
    def _(self, _: NewGameRequestedEvent) -> bool:
        """
        Handles the NewGameRequestedEvent. Resets the board controller and starts a new match.
        """
        if self.model.count_occupied_slots() > 0 and self.model.game_over_condition is None:
            if self._main_window.confirm_abort():
                _logger.info("Current match aborted!")
            else:
                return True
        _logger.info("Starting new match.")
        self._board_controller.reset()
        self._board_controller.start_match()
        return True

    @handle_event.register
    def _(self, _: ScreenshotRequestedEvent) -> bool:
        """
        Handles the ScreenshotRequestedEvent. Captures a screenshot of the game board.
        """
        suggested_path = f"{os.getcwd()}/shiftago_qt_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        file_name = QFileDialog.getSaveFileName(self._main_window, f"{_MainWindow.TITLE} Screenshot",
                                                suggested_path, "Images (*.png *.jpg)")[0]
        if file_name:
            pixmap = QApplication.primaryScreen().grabWindow(self._main_window.board_view.winId())
            pixmap.save(file_name, "PNG" if file_name.lower().endswith(".png") else "JPG", 90)
        return True

    @handle_event.register
    def _(self, _: ExitRequestedEvent) -> bool:
        """
        Handles the ExitRequestedEvent. Asks the user to confirm the exit and closes the application
        if he does so.
        """
        if self.model.count_occupied_slots() > 0:
            if self._main_window.confirm_exit():
                if self.model.game_over_condition is None:
                    _logger.info("Current match aborted!")
            else:
                return True
        QApplication.quit()
        return True


class ShiftagoQtExpress(QApplication):
    """
    ShiftagoQtExpress is the main application class for the Shiftago-Qt Express game.
    It initializes the main window and the main window controller, and starts the application.
    """

    def __init__(self, config: ShiftagoConfig) -> None:
        """
        Initializes the ShiftagoQtExpress application with the given configuration.
        """
        super().__init__()
        self._main_window = _MainWindow(config)
        self._main_window_controller = _MainWindowController(config, self._main_window)
