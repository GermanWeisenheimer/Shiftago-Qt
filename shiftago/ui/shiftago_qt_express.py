from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication, QMainWindow
from shiftago.core import Colour
from shiftago.core.express import ShiftagoExpress
from .hmvc import Controller, AppEvent, AppEventEmitter
from .board_view import BoardView, BOARD_VIEW_SIZE
from .app_events import ExitRequestedEvent
from .game_model import ShiftagoExpressModel
from .board_controller import BoardController


class _MainWindow(AppEventEmitter, QMainWindow):

    def __init__(self, model: ShiftagoExpressModel):
        super().__init__()
        self.setWindowTitle('Shiftago')
        self.setStyleSheet("background-color: lightGray;")
        self.setFixedSize(QSize(BOARD_VIEW_SIZE.width() + 20, BOARD_VIEW_SIZE.height() + 20))
        self._board_view = BoardView(model)
        self.setCentralWidget(self._board_view)

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

    def handle_event(self, event: AppEvent) -> bool:
        if event.__class__ == ExitRequestedEvent:
            self._main_window.close()
            return True
        return False


class ShiftagoQtExpress(QApplication):

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        game_model = ShiftagoExpressModel(ShiftagoExpress((Colour.BLUE, Colour.ORANGE),
                                                          current_player=Colour.BLUE))
        self._main_window = _MainWindow(game_model)
        self._main_window_controller = _MainWindowController(self._main_window, game_model)
