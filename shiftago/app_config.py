import logging
from configparser import ConfigParser
from dataclasses import dataclass
from .core import Colour
from .core.ai_engine import SkillLevel

_CONFIG_FILE = 'shiftago-qt.cfg'

_SECTION_SHIFTAGO = 'shiftago'
_OPT_PREFERRED_COLOUR = 'preferred_colour'

_SECTION_LOGGIMG = 'logging'
_OPT_LOG_LEVEL = 'level'

_SECTION_AI_ENGINE = 'ai_engine'
_OPT_SKILL_LEVEL = 'skill_level'

_logger = logging.getLogger(__name__)


@dataclass
class ShiftagoQtConfig:
    preferred_colour = Colour.BLUE
    log_level = logging.INFO
    ai_engine_skill_level = SkillLevel.ADVANCED


def _parse_preferred_colour(config_parser: ConfigParser, fallback: Colour) -> Colour:
    try:
        section_ai_engine = config_parser[_SECTION_SHIFTAGO]
        str_val = section_ai_engine.get(_OPT_PREFERRED_COLOUR, fallback.name)
        try:
            colour = Colour[str_val]
            if not colour in (Colour.BLUE, Colour.ORANGE):
                _logger.error("Colour '%s' not yet supported.", colour.name)
                return fallback
        except KeyError:
            _logger.error("Option '%s' in section '%s' has illegal value: %s",
                          _OPT_PREFERRED_COLOUR, _SECTION_SHIFTAGO, str_val)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_SHIFTAGO)
    return fallback


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


def _parse_ai_engine_skill_level(config_parser: ConfigParser, fallback: SkillLevel) -> SkillLevel:
    try:
        section_ai_engine = config_parser[_SECTION_AI_ENGINE]
        str_val = section_ai_engine.get(_OPT_SKILL_LEVEL, fallback.name)
        try:
            return SkillLevel[str_val]
        except KeyError:
            _logger.error("Option '%s' in section '%s' has illegal value: %s",
                          _OPT_SKILL_LEVEL, _SECTION_AI_ENGINE, str_val)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_AI_ENGINE)
    return fallback


def read_config() -> ShiftagoQtConfig:
    config_parser = ConfigParser()
    cfg = ShiftagoQtConfig()
    if config_parser.read(_CONFIG_FILE) == [_CONFIG_FILE]:
        cfg.preferred_colour = _parse_preferred_colour(config_parser, cfg.preferred_colour)
        cfg.log_level = _parse_log_level(config_parser, cfg.log_level)
        cfg.ai_engine_skill_level = _parse_ai_engine_skill_level(config_parser,
                                                                 cfg.ai_engine_skill_level)
    else:
        _logger.warning("Configuration file '%s' not found.", _CONFIG_FILE)
    return cfg
