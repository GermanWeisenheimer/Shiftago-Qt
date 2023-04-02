from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QMainWindow
from shiftago.ui.hmvc import ViewMixin, Controller
from shiftago.ui.app_events import AppEvent, ExitRequestedEvent
from shiftago.ui.board_view import BoardView, BoardViewModel


class MainWindow(ViewMixin, QMainWindow):

    def __init__(self, model: BoardViewModel):
        super().__init__()
        self.setWindowTitle('Shiftago')
        self.setStyleSheet("background-color: lightGray;")
        self.setFixedSize(QSize(BoardView.TOTAL_SIZE.width() + 20, BoardView.TOTAL_SIZE.height() + 20))
        self._board_view = BoardView(model)
        self.setCentralWidget(self._board_view)

    @property
    def board_view(self) -> BoardView:
        return self._board_view


class MainWindowController(Controller):

    def __init__(self, main_window: MainWindow) -> None:
        super().__init__(None, main_window)
        self._main_window = main_window
        self._main_window.show()

    def handle_event(self, event: AppEvent) -> bool:
        if event.__class__ == ExitRequestedEvent:
            self._main_window.close()
            return True
        return False
