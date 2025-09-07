"""
This module provides a singleton BrowserManager class to manage the lifecycle of a pydoll Chrome browser instance.
"""

import asyncio
from typing import Optional

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions
from pydoll.page import Page


class BrowserManager:
    """
    A singleton class to manage the lifecycle of a pydoll Chrome browser instance.
    This ensures that only one browser process is running, while allowing for multiple isolated contexts.
    """

    _instance: Optional["BrowserManager"] = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        if BrowserManager._instance is not None:
            raise RuntimeError(
                "This class is a singleton! Use get_instance() to get the instance."
            )
        self._browser: Optional[Chrome] = None
        options = ChromiumOptions()
        options.add_argument("--ignore-certificate-errors")
        self._options = options
        BrowserManager._instance = self

    @classmethod
    async def get_instance(cls) -> "BrowserManager":
        """Get the singleton instance of the BrowserManager, creating it if it doesn't exist."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = BrowserManager()
                await cls._instance.start()
        return cls._instance

    async def start(self) -> None:
        """Starts the Chrome browser instance."""
        if self._browser is None:
            self._browser = Chrome(options=self._options)
            await self._browser.start()

    async def stop(self) -> None:
        """Stops the Chrome browser instance and cleans up the singleton."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        BrowserManager._instance = None  # Allow re-creation for cleanup and testing

    async def create_browser_context(self) -> str:
        """Creates a new, isolated browser context."""
        if self._browser is None:
            raise ConnectionError("Browser has not been started. Call start() first.")
        return await self._browser.create_browser_context()

    async def delete_browser_context(self, context_id: str) -> None:
        """Deletes a browser context, clearing all associated data."""
        if self._browser is None:
            raise ConnectionError("Browser has not been started.")
        await self._browser.delete_browser_context(context_id)

    async def new_tab(self, browser_context_id: str) -> Page:
        """Creates a new tab within a specified browser context."""
        if self._browser is None:
            raise ConnectionError("Browser has not been started.")
        return await self._browser.new_tab(browser_context_id=browser_context_id)


async def get_browser_manager() -> BrowserManager:
    """A convenient function to get the BrowserManager singleton instance."""
    return await BrowserManager.get_instance()
