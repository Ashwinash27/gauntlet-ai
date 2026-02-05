"""Gauntlet exceptions."""


class GauntletError(Exception):
    """Base exception for Gauntlet."""


class ConfigError(GauntletError):
    """Configuration error."""


class DetectionError(GauntletError):
    """Detection layer error."""
