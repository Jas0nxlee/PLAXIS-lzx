"""
Custom exceptions for the PLAXIS backend automation.
"""

class PlaxisAutomationError(Exception):
    """Base class for exceptions in this module."""
    pass

class PlaxisConnectionError(PlaxisAutomationError):
    """Raised when there's an issue connecting to the PLAXIS server."""
    pass

class PlaxisConfigurationError(PlaxisAutomationError):
    """Raised for errors in PLAXIS model configuration (geometry, soil, loads, etc.)."""
    pass

class PlaxisCalculationError(PlaxisAutomationError):
    """Raised when a PLAXIS calculation fails or encounters significant errors."""
    pass

class PlaxisOutputError(PlaxisAutomationError):
    """Raised when there's an issue parsing or retrieving PLAXIS output."""
    pass

class PlaxisCliError(PlaxisAutomationError):
    """Raised for errors specific to PLAXIS CLI script execution."""
    pass

class ProjectValidationError(PlaxisAutomationError):
    """Raised when project settings or input data models fail validation."""
    pass
