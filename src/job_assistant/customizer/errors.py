"""Errors raised when CV customization would introduce unsupported claims."""


class CvCustomizationError(ValueError):
    """Base error for an invalid or unsafe CV customization."""


class UnsupportedCvEditError(CvCustomizationError):
    """An edited preview contains content not supported by its source line."""
