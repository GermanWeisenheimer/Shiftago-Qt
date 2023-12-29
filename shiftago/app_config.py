import logging
from typing import NamedTuple
from configparser import ConfigParser

_CONFIG_FILE = 'shiftago-qt.cfg'
_logger = logging.getLogger(__name__)


class ShiftagoQtConfig(NamedTuple):
    log_level: int
    ai_engine_max_depth: int


def _parse_log_level(config_parser: ConfigParser, default_val: int) -> int:
    try:
        cfg_val = config_parser['logging']['level']
        parsed_log_level = logging.getLevelName(cfg_val)
        if isinstance(parsed_log_level, int):
            return parsed_log_level
        _logger.error("Config key 'logging.level' has illegal value: %s", cfg_val)
    except KeyError:
        _logger.warning("Key 'logging.level' not present in configuration file.")
    return default_val


def _parse_ai_engine_max_depth(config_parser: ConfigParser, default_val: int) -> int:
    try:
        cfg_val = config_parser['ai_engine']['max_depth']
        try:
            parsed_max_depth = int(cfg_val)
            if 1 <= parsed_max_depth <= 4:
                return parsed_max_depth
            _logger.error("Config key 'ai_engine.max_depth' has illegal value %s (allowed range: 1..4).",
                          cfg_val)
        except ValueError:
            _logger.error("Config key 'ai_engine.max_depth' has illegal value: %s", cfg_val)
    except KeyError:
        _logger.warning("Key 'ai_engine.max_depth' not present in configuration file.")
    return default_val


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
