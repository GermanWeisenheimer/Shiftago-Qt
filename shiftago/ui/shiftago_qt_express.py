from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication, QMainWindow
from shiftago.core import Colour
from shiftago.core.express import ShiftagoExpress
from shiftago.ui import BOARD_VIEW_SIZE, Controller, AppEvent, AppEventEmitter
from shiftago.ui.game_model import ShiftagoExpressModel
from shiftago.ui.board_controller import BoardController
from shiftago.ui.board_view import BoardView, BoardViewModel, ExitRequestedEvent


class _MainWindow(AppEventEmitter, QMainWindow):

    def __init__(self, model: BoardViewModel):
        super().__init__()
        self.setWindowTitle('Shiftago')
        self.setStyleSheet("background-color: lightGray;")
        self.setFixedSize(QSize(BOARD_VIEW_SIZE.width() + 20, BOARD_VIEW_SIZE.height() + 20))
        self._board_view = BoardView(model)
        self.setCentralWidget(self._board_view)

    @property
    def board_view(self) -> BoardView:
        return self._board_view


class ShiftagoQtExpress(QApplication):

    class MainWindowController(Controller):

        def __init__(self, main_window: _MainWindow) -> None:
            super().__init__(None, main_window)
            self._main_window = main_window
            self._main_window.show()

        def handle_event(self, event: AppEvent) -> bool:
            if event.__class__ == ExitRequestedEvent:
                self._main_window.close()
                return True
            return False

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        game_model = ShiftagoExpressModel(ShiftagoExpress((Colour.BLUE, Colour.ORANGE), current_player=Colour.BLUE))
        self._main_window = _MainWindow(game_model)
        self._main_window_controller = self.MainWindowController(self._main_window)
        self._board_controller = BoardController(self._main_window_controller, game_model, self._main_window.board_view)
