from typing import Dict, Type, Union, List
from app.models.enums import SocialPlatform
from app.collectors.base import BaseCollector
from app.collectors.instagram.collector import InstagramCollector
from app.collectors.x.collector import XCollector
from app.collectors.facebook.collector import FacebookPageCollector
from app.collectors.exceptions import PlatformNotSupportedError


class CollectorRegistry:
    """
    Central registry mapping SocialPlatform enums to platform collector implementations.
    Unregistered platforms automatically raise PlatformNotSupportedError.
    """

    def __init__(self):
        self._collectors: Dict[SocialPlatform, Union[BaseCollector, Type[BaseCollector]]] = {}

    def register(self, platform: SocialPlatform, collector: Union[BaseCollector, Type[BaseCollector]]) -> None:
        """Register a collector instance or class for a platform."""
        self._collectors[platform] = collector

    def get_collector(self, platform: SocialPlatform) -> BaseCollector:
        """
        Retrieve the registered collector instance for a platform.
        Raises PlatformNotSupportedError if no collector is registered.
        """
        if platform not in self._collectors:
            raise PlatformNotSupportedError(f"No collector registered for platform '{platform.value}'")

        collector_item = self._collectors[platform]
        if isinstance(collector_item, type) and issubclass(collector_item, BaseCollector):
            return collector_item(platform=platform)
        elif isinstance(collector_item, BaseCollector):
            return collector_item

        raise PlatformNotSupportedError(f"Invalid collector registered for platform '{platform.value}'")

    def list_supported_platforms(self) -> List[SocialPlatform]:
        """Return a list of currently registered platforms."""
        return list(self._collectors.keys())

    def clear(self) -> None:
        """Clear all registered collectors (used for resetting tests)."""
        self._collectors.clear()


# Default global registry singleton
registry = CollectorRegistry()

# Register real platform collectors
registry.register(SocialPlatform.INSTAGRAM, InstagramCollector)
registry.register(SocialPlatform.X, XCollector)
registry.register(SocialPlatform.FACEBOOK, FacebookPageCollector)
