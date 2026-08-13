"""Errors produced while validating or reading uploaded CV files."""


class ResumeReadError(Exception):
    """Base error for a CV that cannot be safely read."""


class UnsupportedResumeTypeError(ResumeReadError):
    """The uploaded file is not a supported PDF or DOCX document."""


class ResumeFileTooLargeError(ResumeReadError):
    """The uploaded file exceeds the configured size limit."""


class InvalidResumeFileError(ResumeReadError):
    """The file extension and document contents are invalid or inconsistent."""


class EncryptedResumeError(ResumeReadError):
    """The uploaded document is password protected."""


class EmptyResumeTextError(ResumeReadError):
    """No useful selectable text could be extracted from the document."""
