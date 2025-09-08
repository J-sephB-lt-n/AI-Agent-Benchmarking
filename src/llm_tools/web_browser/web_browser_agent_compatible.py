"""
Web browser implementation designed for AI agent frameworks.
Supports persistent sessions across discrete function calls.
"""

import asyncio
import contextlib
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional, Dict

import pydoll.browser.tab
from html2text import HTML2Text
from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions


@dataclass
class BrowserSessionState:
    """State of a single isolated persistent browser session."""

    session_id: str
    browser_tab: pydoll.browser.tab.Tab
    browser_context_id: str
    current_url: str | None = None
    current_page_html: str | None = None
    current_page_text: str | None = None

    _html_to_text: HTML2Text = field(default_factory=HTML2Text)

    def html_to_text(self, html: str) -> str:
        """Extract text from HTML and return it."""
        return self._html_to_text.handle(html)


# Context variable for the current session (used by tools)
current_browser_session: ContextVar[BrowserSessionState | None] = ContextVar(
    "current_browser_session", default=None
)


class BrowserManager:
    """A singleton manager for the global web browser instance."""

    def __init__(self):
        self._browser: Chrome | None = None
        self._sessions: Dict[str, BrowserSessionState] = {}
        self._async_lock = asyncio.Lock()

    async def start_browser(
        self,
        browser_args: list[str] | None = None,
    ) -> None:
        """
        Start the global web browser.

        Args:
            browser_args (list[str]): e.g. '--headless', '--ignore-certificate-errors'
        """
        if self._browser:
            return  # Already started

        browser_args = browser_args or []

        async with self._async_lock:
            if self._browser:
                return  # Double-check after acquiring lock

            browser_options = ChromiumOptions()
            for arg in browser_args:
                browser_options.add_argument(arg)

            self._browser = Chrome(options=browser_options)
            await self._browser.start()

    async def shutdown_browser(self) -> None:
        """Stop the global web browser and cleanup all sessions."""
        if not self._browser:
            return

        async with self._async_lock:
            # Close all active sessions
            for session_id in list(self._sessions.keys()):
                await self._close_session_internal(session_id)

            await self._browser.stop()
            self._browser = None

    async def create_session(self) -> str:
        """
        Create a new isolated browser session.
        Returns the session ID that should be used for subsequent operations.
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start_browser() first.")

        session_id = str(uuid.uuid4())

        # Create isolated browser context (like incognito mode)
        context_id = await self._browser.create_browser_context()
        new_tab = await self._browser.new_tab(browser_context_id=context_id)

        session_state = BrowserSessionState(
            session_id=session_id,
            browser_tab=new_tab,
            browser_context_id=context_id,
        )

        self._sessions[session_id] = session_state
        return session_id

    async def close_session(self, session_id: str) -> None:
        """Close a browser session and cleanup its resources."""
        await self._close_session_internal(session_id)

    async def _close_session_internal(self, session_id: str) -> None:
        """Internal method to close a session."""
        if session_id not in self._sessions:
            return

        session = self._sessions[session_id]

        # Delete the browser context (this closes all tabs in it)
        try:
            await self._browser.delete_browser_context(session.browser_context_id)
        except Exception:
            pass  # Browser might already be closed

        del self._sessions[session_id]

    def get_session(self, session_id: str) -> BrowserSessionState:
        """Get a session by ID."""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")
        return self._sessions[session_id]

    @contextlib.asynccontextmanager
    async def session_context(self, session_id: str):
        """
        Context manager that sets the current session for tool functions.
        This allows tools to work without explicit session IDs.
        """
        session = self.get_session(session_id)
        token = current_browser_session.set(session)
        try:
            yield session
        finally:
            current_browser_session.reset(token)


class WebBrowser:
    """API for creating and managing browser sessions for AI agents."""

    def __init__(self, browser_manager: BrowserManager) -> None:
        self._browser_manager = browser_manager

    async def start(self, browser_args: list[str] | None = None) -> None:
        """Start the browser. Must be called before creating sessions."""
        await self._browser_manager.start_browser(browser_args)

    async def shutdown(self) -> None:
        """Shutdown the browser and all sessions."""
        await self._browser_manager.shutdown_browser()

    async def create_session(self) -> str:
        """
        Create a new isolated browser session for an AI agent.
        Returns session_id that should be passed to tool functions.
        """
        return await self._browser_manager.create_session()

    async def close_session(self, session_id: str) -> None:
        """Close a browser session."""
        await self._browser_manager.close_session(session_id)

    @contextlib.asynccontextmanager
    async def use_session(self, session_id: str):
        """
        Context manager for using a session. Sets up context variables
        so that tool functions can work without explicit session IDs.

        Usage:
            session_id = await browser.create_session()
            async with browser.use_session(session_id):
                await go_to_url("https://example.com")
                await click_element("button")
            await browser.close_session(session_id)
        """
        async with self._browser_manager.session_context(session_id):
            yield

    # Tool functions that work with the current session context
    async def go_to_url(self, url: str, session_id: str | None = None) -> str:
        """
        Navigate to a URL. Can be called with explicit session_id or
        within a use_session() context manager.
        """
        if session_id:
            async with self.use_session(session_id):
                return await self._go_to_url_impl(url)
        else:
            return await self._go_to_url_impl(url)

    async def _go_to_url_impl(self, url: str) -> str:
        """Internal implementation of go_to_url."""
        session = current_browser_session.get()
        if not session:
            raise RuntimeError("No active browser session. Use create_session() first.")

        await session.browser_tab.go_to(url)
        session.current_url = url

        # Get page content
        html = await session.browser_tab.page_source
        session.current_page_html = html
        session.current_page_text = session.html_to_text(html)

        return session.current_page_text

    async def get_current_page_text(self, session_id: str | None = None) -> str:
        """Get the current page as text."""
        if session_id:
            async with self.use_session(session_id):
                return await self._get_current_page_text_impl()
        else:
            return await self._get_current_page_text_impl()

    async def _get_current_page_text_impl(self) -> str:
        """Internal implementation of get_current_page_text."""
        session = current_browser_session.get()
        if not session:
            raise RuntimeError("No active browser session.")

        if session.current_page_text is None:
            # Refresh page content
            html = await session.browser_tab.page_source
            session.current_page_html = html
            session.current_page_text = session.html_to_text(html)

        return session.current_page_text


# Global instance (similar to your main.py pattern)
_browser_manager = BrowserManager()
web_browser = WebBrowser(_browser_manager)


# Standalone tool functions for AI agents (no explicit session management needed)
async def go_to_url(url: str) -> str:
    """
    Tool function: Navigate to a URL in the current browser session.
    Must be called within a browser session context.
    """
    return await web_browser._go_to_url_impl(url)


async def get_current_page_text() -> str:
    """
    Tool function: Get the current page content as text.
    Must be called within a browser session context.
    """
    return await web_browser._get_current_page_text_impl()


# Example usage patterns for AI agents:


async def example_agent_with_explicit_session_management():
    """Example: AI agent managing sessions explicitly."""
    await web_browser.start()

    try:
        # Create session
        session_id = await web_browser.create_session()

        # Agent function calls with explicit session ID
        content = await web_browser.go_to_url("https://example.com", session_id)
        print(f"Page content: {content[:200]}...")

        # More function calls...
        current_content = await web_browser.get_current_page_text(session_id)

        # Close session when done
        await web_browser.close_session(session_id)

    finally:
        await web_browser.shutdown()


async def example_agent_with_context_manager():
    """Example: AI agent using context manager (cleaner for single tasks)."""
    await web_browser.start()

    try:
        session_id = await web_browser.create_session()

        # All tool calls within this context use the same session
        async with web_browser.use_session(session_id):
            content = await go_to_url("https://example.com")
            print(f"Page content: {content[:200]}...")

            current_content = await get_current_page_text()

        await web_browser.close_session(session_id)

    finally:
        await web_browser.shutdown()


async def example_ai_agent_framework_integration():
    """
    Example: How this would integrate with an AI agent framework
    that makes discrete function calls.
    """
    await web_browser.start()

    # Agent framework creates session at start of conversation
    session_id = await web_browser.create_session()

    # Store session_id in agent state/context
    agent_context = {"browser_session_id": session_id}

    try:
        # Simulate agent making discrete function calls
        # Each call can access the persistent session

        # Function call 1
        async with web_browser.use_session(agent_context["browser_session_id"]):
            result1 = await go_to_url("https://news.ycombinator.com")

        # Agent processes result1, decides next action...

        # Function call 2
        async with web_browser.use_session(agent_context["browser_session_id"]):
            result2 = await get_current_page_text()

        # And so on...

    finally:
        # Clean up when agent conversation ends
        await web_browser.close_session(agent_context["browser_session_id"])
        await web_browser.shutdown()
