"""
This module defines the AgentBrowser class, which provides an isolated browsing environment for an AI agent.
"""

from typing import Dict

from pydoll.page import Page

from .browser_manager import BrowserManager, get_browser_manager


class AgentBrowser:
    """
    Represents an isolated browsing environment for a single AI agent.
    Each AgentBrowser instance has its own browser context and manages its own pages (tabs).
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._browser_manager: BrowserManager | None = None
        self._context_id: str | None = None
        self._pages: Dict[str, Page] = {}  # Maps page_id to Page object
        self._page_counter = 0

    async def _get_browser_manager(self) -> BrowserManager:
        if self._browser_manager is None:
            self._browser_manager = await get_browser_manager()
        return self._browser_manager

    async def initialize(self) -> None:
        """
        Initializes the agent's browsing context.
        This must be called before any other browsing operations.
        """
        browser_manager = await self._get_browser_manager()
        self._context_id = await browser_manager.create_browser_context()

    async def new_page(self) -> Page:
        """
        Creates a new page (tab) in the agent's context and returns it.
        """
        if not self._context_id:
            await self.initialize()
        browser_manager = await self._get_browser_manager()
        page = await browser_manager.new_tab(browser_context_id=self._context_id)  # type: ignore
        page_id = f"page_{self._page_counter}"
        self._page_counter += 1
        self._pages[page_id] = page
        return page

    async def refresh_context(self) -> None:
        """
        Deletes the current browser context and creates a new one, effectively clearing all data.
        """
        browser_manager = await self._get_browser_manager()
        if self._context_id:
            await browser_manager.delete_browser_context(self._context_id)
        self._context_id = await browser_manager.create_browser_context()
        self._pages.clear()  # Pages from the old context are no longer valid

    async def close(self) -> None:
        """
        Cleans up the agent's browser context.
        """
        if self._context_id:
            browser_manager = await self._get_browser_manager()
            await browser_manager.delete_browser_context(self._context_id)
            self._context_id = None
        self._pages.clear()
