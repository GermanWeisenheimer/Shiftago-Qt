import logging
from typing import NamedTuple
from configparser import ConfigParser

_CONFIG_FILE = 'shiftago-qt.cfg'

_SECTION_LOGGIMG = 'logging'
_OPT_LOG_LEVEL = 'level'

_SECTION_AI_ENGINE = 'ai_engine'
_OPT_MAX_DEPTH = 'max_depth'

_logger = logging.getLogger(__name__)


class ShiftagoQtConfig(NamedTuple):
    log_level: int
    ai_engine_max_depth: int


def _parse_log_level(config_parser: ConfigParser, fallback: int) -> int:
    try:
        section_logging = config_parser[_SECTION_LOGGIMG]
        str_val = section_logging.get(_OPT_LOG_LEVEL, logging.getLevelName(fallback))
        int_val = logging.getLevelName(str_val)
        if isinstance(int_val, int):
            return int_val
        _logger.error("Option '%s' in section '%s' has illegal value: %s",
                      _OPT_LOG_LEVEL, _SECTION_LOGGIMG, str_val)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_LOGGIMG)
    return fallback


def _parse_ai_engine_max_depth(config_parser: ConfigParser, fallback: int) -> int:
    try:
        section_ai_engine = config_parser[_SECTION_AI_ENGINE]
        try:
            val = section_ai_engine.getint(_OPT_MAX_DEPTH, fallback)
            if 1 <= val <= 4:
                return val
            raise ValueError(f"{val} out of range [1..4]")
        except ValueError as ve:
            _logger.error("Option '%s' in section '%s' has illegal value: %s",
                          _OPT_MAX_DEPTH, _SECTION_AI_ENGINE, ve)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_AI_ENGINE)
    return fallback


def read_config() -> ShiftagoQtConfig:
    config_parser = ConfigParser()
    log_level_to_use = logging.INFO
    ai_engine_max_depth_to_use = 3
    if config_parser.read(_CONFIG_FILE) == [_CONFIG_FILE]:
        log_level_to_use = _parse_log_level(config_parser, log_level_to_use)
        ai_engine_max_depth_to_use = _parse_ai_engine_max_depth(config_parser,
                                                                ai_engine_max_depth_to_use)
    else:
        _logger.warning("Configuration file '%s' not found.", _CONFIG_FILE)
    return ShiftagoQtConfig(log_level=log_level_to_use,
                            ai_engine_max_depth=ai_engine_max_depth_to_use)
