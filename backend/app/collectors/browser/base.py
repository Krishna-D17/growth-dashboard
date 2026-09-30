from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseBrowserDriver(ABC):
    """
    Abstract interface for browser automation engines.
    Isolates platform collectors from direct dependencies on underlying Selenium browser automation.
    """

    @abstractmethod
    def start(self) -> None:
        """Initialize and start the browser instance."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up and close the browser instance."""
        pass

    @abstractmethod
    def fetch_page_content(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        """Navigate to a target URL and return raw HTML page content."""
        pass

    @abstractmethod
    def extract_json(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch endpoint or embedded state JSON content if supported."""
        pass


class MockBrowserDriver(BaseBrowserDriver):
    """
    In-memory mock browser driver for testing and development.
    Returns simulated HTML content without starting headless browser processes.
    """

    def __init__(self, simulated_html: Optional[str] = None):
        self.simulated_html = simulated_html or "<html><body><div id='profile'>Mock Page Content</div></body></html>"
        self.is_started = False

    def start(self) -> None:
        self.is_started = True

    def close(self) -> None:
        self.is_started = False

    def fetch_page_content(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        if not self.is_started:
            self.start()
        return f"<!-- Content from {url} -->\n{self.simulated_html}"

    def extract_json(self, url: str) -> Optional[Dict[str, Any]]:
        return {"mock_url": url, "status": "ok"}
