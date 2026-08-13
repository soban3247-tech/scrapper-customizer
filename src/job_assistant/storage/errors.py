"""Errors raised by local application persistence."""


class StorageError(Exception):
    """Base error for data that could not be safely persisted or loaded."""


class ProfileStorageError(StorageError):
    """A confirmed profile could not be saved or reconstructed."""
