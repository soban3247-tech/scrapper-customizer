"""Default scraper registry used by the application."""

from .arbeitnow import ArbeitnowScraper
from .ashby import AshbyScraper
from .greenhouse import GreenhouseScraper
from .hiringcafe import HiringCafeScraper
from .lever import LeverScraper
from .registry import ScraperRegistry
from .remote_ok import RemoteOkScraper
from .remotive import RemotiveScraper


def create_default_registry() -> ScraperRegistry:
    """Return a fresh registry containing every supported MVP adapter."""

    return ScraperRegistry(
        [
            HiringCafeScraper(),
            RemotiveScraper(),
            ArbeitnowScraper(),
            RemoteOkScraper(),
            GreenhouseScraper(),
            LeverScraper(),
            AshbyScraper(),
        ]
    )
