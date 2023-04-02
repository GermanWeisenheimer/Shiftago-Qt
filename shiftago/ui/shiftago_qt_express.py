import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List
from types import TracebackType
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication
from shiftago.core import Colour
from shiftago.core.express import ShiftagoExpress
from shiftago.ui.game_model import ShiftagoExpressModel
from shiftago.ui.main_window import MainWindow, MainWindowController
from shiftago.ui.board_controller import BoardController

logger = logging.getLogger(__name__)


class _LoggingConfigurer:

    LOGS_DIR = './logs'

    class ThreadNameFilter(logging.Filter):
        '''Adds the name of the current QThread as custom field 'qthreadName'.'''

        def filter(self, record: logging.LogRecord):
            qthread_name = QThread.currentThread().objectName()
            record.qthreadName = qthread_name if qthread_name else record.threadName
            return True

    def __init__(self, filename_prefix: str = 'shiftago_qt') -> None:
        self._filename_prefix = filename_prefix

    def configure(self) -> str:
        Path(self.LOGS_DIR).mkdir(exist_ok=True)
        filename = f"{self.LOGS_DIR}/{self._filename_prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        handlers = [logging.StreamHandler(), logging.FileHandler(filename, mode='w')]
        filter = self.ThreadNameFilter()
        for handler in handlers:
            handler.addFilter(filter)
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s [%(qthreadName)14s] %(name)s %(levelname)5s - %(message)s',
                            handlers=handlers)
        return filename


class ShiftagoQtExpress(QApplication):

    def __init__(self, argv: List[str]) -> None:
        super().__init__(argv)
        shiftago = ShiftagoExpress((Colour.BLUE, Colour.ORANGE), current_player=Colour.BLUE)
        game_model = ShiftagoExpressModel(shiftago)
        self._main_window = MainWindow(game_model)
        self._main_window_controller = MainWindowController(self._main_window)
        self._board_controller = BoardController(self._main_window_controller, game_model, self._main_window.board_view)


if __name__ == '__main__':
    def handle_uncaught_exception(exc_type: type[BaseException], exc_value: BaseException,
                                  exc_traceback: TracebackType | None):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.fatal("Uncaught exception!", exc_info=(exc_type, exc_value, exc_traceback))
        sys.exit(1)

    sys.excepthook = handle_uncaught_exception
    print(f"Writing log file {_LoggingConfigurer().configure()}")
    sys.exit(ShiftagoQtExpress(sys.argv).exec())
