import logging
from configparser import ConfigParser, SectionProxy
from dataclasses import dataclass
from pathlib import Path
from .core import Colour, SkillLevel

_CONFIG_FILE = 'shiftago-qt.cfg'

_SECTION_SHIFTAGO = 'shiftago'
_OPT_PREFERRED_COLOUR = 'preferred_colour'
_OPT_SKILL_LEVEL = 'skill_level'

_SECTION_LOGGING = 'logging'
_OPT_LOGS_DIR = 'logs_dir'
_OPT_LOG_LEVEL = 'level'

_logger = logging.getLogger(__name__)


@dataclass
class ShiftagoConfig:
    """
    ShiftagoConfig holds the configuration settings for the Shiftago game.

    Attributes:
    preferred_colour (Colour): The preferred colour of the player.
    skill_level (SkillLevel): The skill level of the AI.
    """
    preferred_colour: Colour = Colour.BLUE
    skill_level: SkillLevel = SkillLevel.ADVANCED


@dataclass
class LoggingConfig:
    """
    LoggingConfig holds the configuration settings for logging.

    Attributes:
    logs_dir (str): The directory where log files will be stored.
    log_level (int): The logging level.
    """
    logs_dir = './logs'
    log_level = logging.INFO


@dataclass(frozen=True)
class ShiftagoAppConfig:
    """
    ShiftagoAppConfig holds the overall configuration settings for the Shiftago application.

    Attributes:
    shiftago (ShiftagoConfig): The configuration settings for the Shiftago game.
    logging (LoggingConfig): The configuration settings for logging.
    """
    shiftago = ShiftagoConfig()
    logging = LoggingConfig()


def _parse_preferred_colour(section: SectionProxy, fallback: Colour) -> Colour:
    """
    Parses the preferred colour from the configuration section.
    """
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
    """
    Parses the skill level from the configuration section.
    """
    str_val = section.get(_OPT_SKILL_LEVEL, fallback.name)
    try:
        return SkillLevel[str_val]
    except KeyError:
        _logger.error("Option '%s' in section '%s' has illegal value: %s",
                      _OPT_SKILL_LEVEL, section.name, str_val)
    return fallback


def _parse_section_shiftago(config_parser: ConfigParser, shiftago_cfg: ShiftagoConfig) -> None:
    """
    Parses the Shiftago section from the configuration file and updates the ShiftagoConfig object.
    """
    try:
        section = config_parser[_SECTION_SHIFTAGO]
        shiftago_cfg.preferred_colour = _parse_preferred_colour(section, shiftago_cfg.preferred_colour)
        shiftago_cfg.skill_level = _parse_skill_level(section, shiftago_cfg.skill_level)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_SHIFTAGO)


def _parse_logs_dir(section: SectionProxy, fallback: str) -> str:
    """
    Parses the logs directory from the configuration section.
    """
    str_val = section.get(_OPT_LOGS_DIR, fallback)
    logs_dir = Path(str_val)
    try:
        logs_dir.mkdir(exist_ok=True)
        return str_val
    except OSError as e:
        _logger.error("%s: %s", e.strerror, e.filename)
    return fallback


def _parse_log_level(section: SectionProxy, fallback: int) -> int:
    """
    Parses the log level from the configuration section.
    """
    str_val = section.get(_OPT_LOG_LEVEL, logging.getLevelName(fallback))
    int_val = logging.getLevelName(str_val)
    if isinstance(int_val, int):
        return int_val
    _logger.error("Option '%s' in section '%s' has illegal value: %s", _OPT_LOG_LEVEL, section.name, str_val)
    return fallback


def _parse_section_logging(config_parser: ConfigParser, logging_cfg: LoggingConfig) -> None:
    """
    Parses the logging section from the configuration file and updates the LoggingConfig object.
    """
    try:
        section = config_parser[_SECTION_LOGGING]
        logging_cfg.logs_dir = _parse_logs_dir(section, logging_cfg.logs_dir)
        logging_cfg.log_level = _parse_log_level(section, logging_cfg.log_level)
    except KeyError:
        _logger.warning("Section '%s' not present in configuration file.", _SECTION_LOGGING)


def read_config() -> ShiftagoAppConfig:
    """
    Reads the configuration settings from the configuration file.
    """
    config_parser = ConfigParser()
    config = ShiftagoAppConfig()
    if config_parser.read(_CONFIG_FILE) == [_CONFIG_FILE]:
        _parse_section_shiftago(config_parser, config.shiftago)
        _parse_section_logging(config_parser, config.logging)
    else:
        _logger.warning("Configuration file '%s' not found.", _CONFIG_FILE)
    return config
