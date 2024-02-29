import logging
import os
from datetime import datetime
from functools import singledispatchmethod
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog
from PySide6.QtGui import QIcon, QAction
from shiftago.app_config import ShiftagoConfig
from shiftago.core import Colour
from shiftago.ui import load_image, Controller, AppEvent, AppEventEmitter
from .board_view import BoardView, BOARD_VIEW_SIZE
from .app_events import NewGameRequestedEvent, ScreenshotRequestedEvent, ExitRequestedEvent
from .game_model import ShiftagoExpressModel, PlayerNature, Player
from .board_controller import BoardController

_logger = logging.getLogger(__name__)


def _build_model(config: ShiftagoConfig) -> ShiftagoExpressModel:
    humans_colour = config.preferred_colour
    computers_colour = Colour.ORANGE if humans_colour is Colour.BLUE else Colour.BLUE
    return ShiftagoExpressModel((Player(humans_colour, PlayerNature.HUMAN),
                                 Player(computers_colour, PlayerNature.ARTIFICIAL)), config)


class _MainWindow(AppEventEmitter, QMainWindow):

    TITLE = 'Shiftago-Qt'

    def __init__(self, config: ShiftagoConfig):
        super().__init__()
        self._model = _build_model(config)
        self.setWindowTitle(self.TITLE)
        self.setStyleSheet("background-color: lightGray;")
        self.setFixedSize(QSize(BOARD_VIEW_SIZE.width() + 28, BOARD_VIEW_SIZE.height() + 34))
        self._board_view = BoardView(self._model, self.TITLE)
        self.setCentralWidget(self._board_view)
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('New game', lambda: self.emit(NewGameRequestedEvent()))
        file_menu.addAction('Screenshot', lambda: self.emit(ScreenshotRequestedEvent()))
        exit_action = QAction(QIcon(load_image('exit-icon.png')), '&Exit', self)
        exit_action.triggered.connect(lambda: self.emit(ExitRequestedEvent()))
        file_menu.addAction(exit_action)
        self._exit_confirmed = False

    def closeEvent(self, event):  # pylint: disable=invalid-name
        if not self._exit_confirmed:
            event.ignore()
            self.emit(ExitRequestedEvent())

    def confirm_abort(self) -> bool:
        reply = QMessageBox.question(self, self.TITLE, 'Are you sure you want to abort the current game?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    def confirm_exit(self) -> bool:
        reply = QMessageBox.question(self, self.TITLE, 'Are you sure you want to quit?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._exit_confirmed = True
        return self._exit_confirmed

    @property
    def board_view(self) -> BoardView:
        return self._board_view

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._model


class _MainWindowController(Controller):

    def __init__(self, config: ShiftagoConfig, main_window: _MainWindow) -> None:
        super().__init__(None, main_window)
        self._config = config
        self._board_controller = BoardController(self, main_window.model, main_window.board_view)
        self._main_window = main_window
        self._main_window.show()
        self._board_controller.start_match()

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._main_window.model

    @singledispatchmethod
    def handle_event(self, _: AppEvent) -> bool:
        return False

    @handle_event.register
    def _(self, _: NewGameRequestedEvent) -> bool:
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
        suggested_path = f"{os.getcwd()}/shiftago_qt_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
        file_name = QFileDialog.getSaveFileName(self._main_window, "Save screenshot",
                                                suggested_path, "Images (*.png *.jpg)")[0]
        if file_name:
            pixmap = QApplication.primaryScreen().grabWindow(self._main_window.board_view.winId())
            pixmap.save(file_name, "PNG" if file_name.lower().endswith(".png") else "JPG", 90)
        return True

    @handle_event.register
    def _(self, _: ExitRequestedEvent) -> bool:
        if self.model.count_occupied_slots() > 0:
            if self._main_window.confirm_exit():
                if self.model.game_over_condition is None:
                    _logger.info("Current match aborted!")
            else:
                return True
        QApplication.quit()
        return True


class ShiftagoQtExpress(QApplication):

    def __init__(self, config: ShiftagoConfig) -> None:
        super().__init__()
        self._main_window = _MainWindow(config)
        self._main_window_controller = _MainWindowController(config, self._main_window)
