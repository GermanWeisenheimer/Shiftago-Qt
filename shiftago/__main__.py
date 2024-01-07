import sys
import logging
from datetime import datetime
from types import TracebackType
from PySide2.QtCore import QThread
from .app_config import read_config, LoggingConfig
from .ui.shiftago_qt_express import ShiftagoQtExpress

_logger = logging.getLogger(__name__)


def _is_writable(file_path: str) -> bool:
    try:
        with open(file_path, "w"):  # pylint: disable=unspecified-encoding
            return True
    except OSError:
        return False


def _configure_logging(config: LoggingConfig, filename_prefix: str = 'shiftago_qt'):
    '''Adds the name of the current QThread as field 'threadName'.'''
    def thread_name_filter(record: logging.LogRecord):
        qthread_name = QThread.currentThread().objectName()
        if qthread_name:
            record.threadName = qthread_name
        return True
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    file_path = f"{config.logs_dir}/{filename_prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    if _is_writable(file_path):
        handlers.append(logging.FileHandler(file_path, mode='w'))
        print(f"Writing log file: {file_path}")
    else:
        print(f"Directory {config.logs_dir} is not writable!")
    for handler in handlers:
        handler.addFilter(thread_name_filter)
    logging.basicConfig(level=config.log_level,
                        format='%(asctime)s [%(threadName)14s] %(name)s %(levelname)5s - %(message)s',
                        handlers=handlers)


def main() -> None:
    def handle_uncaught_exception(exc_type: type[BaseException], exc_value: BaseException,
                                  exc_traceback: TracebackType | None):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        _logger.fatal("Uncaught exception!", exc_info=(exc_type, exc_value, exc_traceback))
        sys.exit(1)

    sys.excepthook = handle_uncaught_exception
    app_config = read_config()
    _configure_logging(config=app_config.logging)
    sys.exit(ShiftagoQtExpress(app_config.shiftago).exec_())


if __name__ == '__main__':
    main()
