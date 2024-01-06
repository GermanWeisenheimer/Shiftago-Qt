import logging
from configparser import ConfigParser, SectionProxy
from dataclasses import dataclass
from .core import Colour
from .core.ai_engine import SkillLevel

_CONFIG_FILE = 'shiftago-qt.cfg'

_SECTION_SHIFTAGO = 'shiftago'
_OPT_PREFERRED_COLOUR = 'preferred_colour'
_OPT_SKILL_LEVEL = 'skill_level'

_SECTION_LOGGIMG = 'logging'
_OPT_LOG_LEVEL = 'level'


_logger = logging.getLogger(__name__)


@dataclass
class ShiftagoConfig:
    preferred_colour = Colour.BLUE
    skill_level = SkillLevel.ADVANCED


@dataclass
class LoggingConfig:
    log_level = logging.INFO


@dataclass(frozen=True)
class ShiftagoQtConfig:
    shiftago = ShiftagoConfig()
    logging = LoggingConfig()


def _parse_prerred_colour(section: SectionProxy, fallback: Colour) -> Colour:
    str_val = section.get(_OPT_PREFERRED_COLOUR, fallback.name)
    try:
        colour = Colour[str_val]
        if colour in (Colour.BLUE, Colour.ORANGE):
            return colour
        _logger.error("Colour '%s' not yet supported.", colour.name)
    except KeyError:
        _logger.error("Option '%s' in section '%s' has illegal value: %s",
                      _OPT_PREFERRED_COLOUR, section.name, str_val)
    return fallback


def _parse_skill_level(section: SectionProxy, fallback: SkillLevel) -> SkillLevel:
    str_val = section.get(_OPT_SKILL_LEVEL, fallback.name)
    try:
        return SkillLevel[str_val]
    except KeyError:
        _logger.error("Option '%s' in section '%s' has illegal value: %s",
                      _OPT_SKILL_LEVEL, section.name, str_val)
    return fallback


def _parse_section_shiftago(config_parser: ConfigParser, shiftago_cfg: ShiftagoConfig) -> None:
    try:
        section = config_parser[_SECTION_SHIFTAGO]
        shiftago_cfg.preferred_colour = _parse_prerred_colour(section, shiftago_cfg.preferred_colour)
        shiftago_cfg.skill_level = _parse_skill_level(section, shiftago_cfg.skill_level)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_SHIFTAGO)


def _parse_section_logging(config_parser: ConfigParser, logging_cfg: LoggingConfig) -> None:
    try:
        section = config_parser[_SECTION_LOGGIMG]
        str_val = section.get(_OPT_LOG_LEVEL, logging.getLevelName(logging_cfg.log_level))
        int_val = logging.getLevelName(str_val)
        if isinstance(int_val, int):
            logging_cfg.log_level = int_val
        else:
            _logger.error("Option '%s' in section '%s' has illegal value: %s",
                          _OPT_LOG_LEVEL, section.name, str_val)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_LOGGIMG)


def read_config() -> ShiftagoQtConfig:
    config_parser = ConfigParser()
    config = ShiftagoQtConfig()
    if config_parser.read(_CONFIG_FILE) == [_CONFIG_FILE]:
        _parse_section_shiftago(config_parser, config.shiftago)
        _parse_section_logging(config_parser, config.logging)
    else:
        _logger.warning("Configuration file '%s' not found.", _CONFIG_FILE)
    return config
