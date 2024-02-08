import logging
from functools import singledispatchmethod
from PySide2.QtCore import QSize
from PySide2.QtWidgets import QApplication, QMainWindow, QMessageBox
from shiftago.app_config import ShiftagoConfig
from shiftago.core import Colour
from .hmvc import Controller, AppEvent, AppEventEmitter
from .board_view import BoardView, BOARD_VIEW_SIZE
from .app_events import NewMatchRequestedEvent, ExitRequestedEvent
from .game_model import ShiftagoExpressModel, PlayerNature, Player
from .board_controller import BoardController

_logger = logging.getLogger(__name__)


class _MainWindow(AppEventEmitter, QMainWindow):

    TITLE = 'Shiftago-Qt'

    def __init__(self, model: ShiftagoExpressModel):
        super().__init__()
        self._model = model
        self.setWindowTitle(self.TITLE)
        self.setStyleSheet("background-color: lightGray;")
        self.setFixedSize(QSize(BOARD_VIEW_SIZE.width() + 20, BOARD_VIEW_SIZE.height() + 20))
        self._board_view = BoardView(model, self.TITLE)
        self.setCentralWidget(self._board_view)
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('New match', lambda: self.emit(NewMatchRequestedEvent()))
        file_menu.addAction('Exit', lambda: self.emit(ExitRequestedEvent()))

    def closeEvent(self, event):  # pylint: disable=invalid-name
        event.ignore()
        self.emit(ExitRequestedEvent())

    def confirm_abort(self) -> bool:
        reply = QMessageBox.question(self, self.TITLE, 'Are you sure you want to abort the current match?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def confirm_exit(self) -> bool:
        reply = QMessageBox.question(self, self.TITLE, 'Are you sure you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    @property
    def board_view(self) -> BoardView:
        return self._board_view

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._model

    @model.setter
    def model(self, new_model: ShiftagoExpressModel) -> None:
        self._model = new_model
        self._board_view.model = new_model


class _MainWindowController(Controller):

    def __init__(self, config: ShiftagoConfig, main_window: _MainWindow) -> None:
        super().__init__(None, main_window)
        self._config = config
        self._model = main_window.model
        self._board_controller = BoardController(self, main_window.model, main_window.board_view)
        self._main_window = main_window
        self._main_window.show()
        self._board_controller.start_game()

    @staticmethod
    def build_model(config: ShiftagoConfig) -> ShiftagoExpressModel:
        humans_colour = config.preferred_colour
        computers_colour = Colour.ORANGE if humans_colour is Colour.BLUE else Colour.BLUE
        return ShiftagoExpressModel((Player(humans_colour, PlayerNature.HUMAN),
                                     Player(computers_colour, PlayerNature.ARTIFICIAL)), config)

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._board_controller.model

    @singledispatchmethod
    def handle_event(self, _: AppEvent) -> bool:
        return False

    @handle_event.register
    def _(self, _: NewMatchRequestedEvent) -> bool:  # pylint: disable=unused-argument
        if self._model.count_occupied_slots() > 0 and self._model.game_over_condition is None:
            if self._main_window.confirm_abort():
                _logger.info("Current match aborted!")
            else:
                return True
        self._model = self.build_model(self._config)
        self._main_window.model = self._model
        self._board_controller.model = self._model
        self._board_controller.start_game()
        return True

    @handle_event.register
    def _(self, _: ExitRequestedEvent) -> bool:  # pylint: disable=unused-argument
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
        self._main_window = _MainWindow(_MainWindowController.build_model(config))
        self._main_window_controller = _MainWindowController(config, self._main_window)
