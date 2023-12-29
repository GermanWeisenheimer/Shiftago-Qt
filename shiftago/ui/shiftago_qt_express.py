from PySide2.QtCore import QSize
from PySide2.QtWidgets import QApplication, QMainWindow, QMessageBox
from shiftago.app_config import ShiftagoQtConfig
from shiftago.core import Colour
from shiftago.core.express import ShiftagoExpress
from .hmvc import Controller, AppEvent, AppEventEmitter
from .board_view import BoardView, BOARD_VIEW_SIZE
from .app_events import ExitRequestedEvent
from .game_model import ShiftagoExpressModel
from .board_controller import BoardController


class _MainWindow(AppEventEmitter, QMainWindow):

    TITLE = 'Shiftago-Qt'

    def __init__(self, model: ShiftagoExpressModel):
        super().__init__()
        self.setWindowTitle(self.TITLE)
        self.setStyleSheet("background-color: lightGray;")
        self.setFixedSize(QSize(BOARD_VIEW_SIZE.width() + 20, BOARD_VIEW_SIZE.height() + 20))
        self._board_view = BoardView(model, self.TITLE)
        self.setCentralWidget(self._board_view)

    def closeEvent(self, event):  # pylint: disable=invalid-name
        event.ignore()
        self.emit(ExitRequestedEvent())

    def confirm_exit(self) -> bool:
        reply = QMessageBox.question(self, self.TITLE, 'Are you sure you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    @property
    def board_view(self) -> BoardView:
        return self._board_view


class _MainWindowController(Controller):

    def __init__(self, main_window: _MainWindow, model: ShiftagoExpressModel) -> None:
        super().__init__(None, main_window)
        self._board_controller = BoardController(self, model, main_window.board_view)
        self._main_window = main_window
        self._main_window.show()
        self._board_controller.start_game()

    @property
    def model(self) -> ShiftagoExpressModel:
        return self._board_controller.model

    def handle_event(self, event: AppEvent) -> bool:
        if isinstance(event, ExitRequestedEvent):
            if self.model.count_occupied_slots() > 0:
                if self._main_window.confirm_exit():
                    QApplication.quit()
            else:
                QApplication.quit()
            return True
        return False


class ShiftagoQtExpress(QApplication):

    def __init__(self, app_config: ShiftagoQtConfig) -> None:
        super().__init__()
        game_model = ShiftagoExpressModel(ShiftagoExpress((Colour.BLUE, Colour.ORANGE),
                                                          current_player=Colour.BLUE), app_config)
        self._main_window = _MainWindow(game_model)
        self._main_window_controller = _MainWindowController(self._main_window, game_model)
