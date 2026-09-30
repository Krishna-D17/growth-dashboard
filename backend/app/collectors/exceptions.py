class CollectorError(Exception):
    """Base exception for all SocialScope collector errors."""
    pass


class TargetValidationError(CollectorError):
    """Raised when a collection target URL or handle format is invalid."""
    pass


class PlatformNotSupportedError(CollectorError):
    """Raised when no collector is registered for the requested platform."""
    pass


class RateLimitError(CollectorError):
    """Raised when the platform collector encounters a rate limit barrier."""
    pass


class ContentUnavailableError(CollectorError):
    """Raised when a targeted profile or post is private, deleted, or unavailable."""
    pass


class CollectorExecutionError(CollectorError):
    """Raised when a non-fatal or fatal error occurs during collector execution."""
    pass
