import sys
import logging
from pathlib import Path
from datetime import datetime
from types import TracebackType
from PySide2.QtCore import QThread
from .ui.shiftago_qt_express import ShiftagoQtExpress

_logger = logging.getLogger(__name__)


def _configure_logging(*, logs_dir: str = './logs', filename_prefix: str = 'shiftago_qt') -> str:
    '''Adds the name of the current QThread as field 'threadName'.'''
    def thread_name_filter(record: logging.LogRecord):
        qthread_name = QThread.currentThread().objectName()
        if qthread_name:
            record.threadName = qthread_name
        return True
    Path(logs_dir).mkdir(exist_ok=True)
    filename = f"{logs_dir}/{filename_prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    handlers = [logging.StreamHandler(), logging.FileHandler(filename, mode='w')]
    for handler in handlers:
        handler.addFilter(thread_name_filter)
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(threadName)14s] %(name)s %(levelname)5s - %(message)s',
                        handlers=handlers)
    return filename


if __name__ == '__main__':
    def handle_uncaught_exception(exc_type: type[BaseException], exc_value: BaseException,
                                  exc_traceback: TracebackType | None):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        _logger.fatal("Uncaught exception!", exc_info=(exc_type, exc_value, exc_traceback))
        sys.exit(1)

    sys.excepthook = handle_uncaught_exception
    print(f"Writing log file {_configure_logging()}")
    sys.exit(ShiftagoQtExpress(sys.argv).exec_())
