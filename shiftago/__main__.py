import sys
import logging
from pathlib import Path
from datetime import datetime
from types import TracebackType
from PyQt5.QtCore import QThread
from shiftago.ui.shiftago_qt_express import ShiftagoQtExpress

logger = logging.getLogger(__name__)


class _LoggingConfigurer:

    LOGS_DIR = './logs'

    def __init__(self, filename_prefix: str = 'shiftago_qt') -> None:
        self._filename_prefix = filename_prefix

    @property
    def filename_prefix(self) -> str:
        return self._filename_prefix

    def configure(self) -> str:
        '''Adds the name of the current QThread as custom field 'qthreadName'.'''
        def thread_name_filter(record: logging.LogRecord):
            qthread_name = QThread.currentThread().objectName()
            record.qthreadName = qthread_name if qthread_name else record.threadName
            return True
        Path(self.LOGS_DIR).mkdir(exist_ok=True)
        filename = f"{self.LOGS_DIR}/{self.filename_prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        handlers = [logging.StreamHandler(), logging.FileHandler(filename, mode='w')]
        for handler in handlers:
            handler.addFilter(thread_name_filter)
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s [%(qthreadName)14s] %(name)s %(levelname)5s - %(message)s',
                            handlers=handlers)
        return filename


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
