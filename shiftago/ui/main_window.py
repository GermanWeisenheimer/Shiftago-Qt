import sys
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
        self._board = BoardView(model)
        self.setCentralWidget(self._board)
        self.show()

    @property
    def board_view(self) -> BoardView:
        return self._board


class MainWindowController(Controller):

    def __init__(self, view: MainWindow) -> None:
        super().__init__(None, view)
        self._view = view

    def handle_event(self, event: AppEvent) -> bool:
        if event.__class__ == ExitRequestedEvent:
            sys.exit(0)
        return False
