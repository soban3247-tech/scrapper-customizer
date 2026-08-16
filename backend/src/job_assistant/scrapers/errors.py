"""Shared exceptions raised by scraper adapters and the scraper registry."""


class ScraperError(Exception):
    """Base error for a known scraper failure."""

    code = "scraper_error"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or type(self).code
        self.retryable = type(self).retryable if retryable is None else retryable


class ScraperConfigurationError(ScraperError):
    """The selected scraper is missing required user configuration."""

    code = "configuration_error"


class ScraperRequestError(ScraperError):
    """A remote job source could not be reached successfully."""

    code = "request_error"
    retryable = True


class ScraperResponseError(ScraperError):
    """A job source returned data the adapter could not understand."""

    code = "response_error"


class ScraperContractError(ScraperError):
    """A scraper adapter violated the common external contract."""

    code = "contract_error"


class ScraperRegistrationError(ScraperError):
    """A scraper could not be added to the registry."""

    code = "registration_error"


class ScraperNotFoundError(ScraperError):
    """No registered adapter matches a requested source identifier."""

    code = "scraper_not_found"

