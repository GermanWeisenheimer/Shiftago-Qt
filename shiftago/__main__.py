import sys
import logging
from configparser import ConfigParser
from pathlib import Path
from datetime import datetime
from types import TracebackType
from typing import NamedTuple
from PySide2.QtCore import QThread
from .ui.shiftago_qt_express import ShiftagoQtExpress

_CONFIG_FILE = 'shiftago-qt.cfg'
_logger = logging.getLogger(__name__)


class _ShiftagoConfig(NamedTuple):
    log_level: int


def _read_config() -> _ShiftagoConfig:
    config_parser = ConfigParser()
    log_level_to_use = logging.INFO
    if config_parser.read(_CONFIG_FILE):
        try:
            parsed_log_level = logging.getLevelName(config_parser['logging']['level'])
            if isinstance(parsed_log_level, int):
                log_level_to_use = parsed_log_level
            else:
                _logger.error("Illegal logging level in configuration file: %s", parsed_log_level)
        except KeyError:
            _logger.warning("Logging level not present in configuration file.")
    else:
        _logger.warning("Configuration file '%s' not found.", _CONFIG_FILE)
    return _ShiftagoConfig(log_level=log_level_to_use)


def _configure_logging(*, logs_dir: str = './logs', filename_prefix: str = 'shiftago_qt',
                       config: _ShiftagoConfig) -> str:
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
    logging.basicConfig(level=config.log_level,
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
    cfg = _read_config()
    print(f"Writing log file {_configure_logging(config=cfg)}")
    sys.exit(ShiftagoQtExpress(sys.argv).exec_())
