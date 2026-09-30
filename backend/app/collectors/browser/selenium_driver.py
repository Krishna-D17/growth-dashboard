import json
from typing import Optional, Dict, Any
from app.collectors.browser.base import BaseBrowserDriver
from app.config import settings


class SeleniumBrowserDriver(BaseBrowserDriver):
    """
    Concrete Selenium implementation of BaseBrowserDriver using Chrome/Chromium.
    Uses Selenium 4.x automatic driver management and ephemeral browser sessions.
    Configured with 'eager' page load strategy to avoid renderer timeouts on heavy JS pages.
    """

    def __init__(self, headless: Optional[bool] = None, timeout: Optional[int] = None):
        self.headless = settings.browser_headless if headless is None else headless
        self.timeout = settings.browser_timeout if timeout is None else timeout
        self._driver = None
        self._is_started = False

    def start(self) -> None:
        """Initialize and launch the Selenium Chrome WebDriver instance."""
        if self._is_started and self._driver:
            return

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.page_load_strategy = "eager"
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1280,800")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-background-networking")
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )

            self._driver = webdriver.Chrome(options=options)
            timeout_sec = max(1.0, self.timeout / 1000.0)
            self._driver.set_page_load_timeout(timeout_sec)
            self._driver.set_script_timeout(timeout_sec)
            self._is_started = True
        except Exception as e:
            self.close()
            raise RuntimeError(f"Failed to launch Selenium Chrome browser driver: {str(e)}") from e

    def close(self) -> None:
        """Clean up and close the Selenium WebDriver instance."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
        self._is_started = False

    def fetch_page_content(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        """Navigate to target URL in an ephemeral browser session and return page source HTML."""
        if not self._is_started or not self._driver:
            self.start()

        try:
            try:
                self._driver.get(url)
            except Exception as nav_err:
                err_msg = str(nav_err).lower()
                if ("timeout" in err_msg or "renderer" in err_msg) and self._driver:
                    try:
                        source = self._driver.page_source
                        if source and len(source.strip()) > 200:
                            return source
                    except Exception:
                        pass
                raise nav_err

            if wait_for_selector:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                timeout_sec = max(1.0, self.timeout / 1000.0)
                WebDriverWait(self._driver, timeout_sec).until(
                    EC.presence_of_element_locator((By.CSS_SELECTOR, wait_for_selector))
                )

            return self._driver.page_source
        except Exception as e:
            self.close()
            raise RuntimeError(f"Selenium fetch_page_content failed for URL '{url}': {str(e)}") from e

    def extract_json(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch endpoint or page content and parse JSON if available."""
        content = self.fetch_page_content(url)
        try:
            return json.loads(content)
        except Exception:
            return None

