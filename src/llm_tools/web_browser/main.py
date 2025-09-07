# main.py

import asyncio
import contextlib
import contextvars
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions

# -- Part 1: Architectural Components --
# This section contains the core infrastructure for managing the browser and sessions.

# 1a. Session State and Context Variable
# A dataclass to hold the state for a single isolated session.
# The context variable `current_session` makes this state implicitly available
# to any function called within an `isolated_session` block.


@dataclass
class BrowserSessionState:
    """Represents the state of a single, isolated browser session."""

    browser_context_id: str
    active_page_id: str
    all_page_ids: list[str] = field(default_factory=list)


# The "magic" context variable. It's None outside of a session.
current_session: contextvars.ContextVar[Optional[BrowserSessionState]] = (
    contextvars.ContextVar("current_session", default=None)
)


# 1b. The Singleton Browser Manager
# Manages the single, long-lived Chrome process and all its pages.


class BrowserManager:
    """A singleton manager for the underlying pydoll Chrome instance."""

    def __init__(self):
        self._browser: Optional[Chrome] = None
        # This registry maps our internal page IDs to the live pydoll page objects.
        self._pages: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def start(self):
        """Starts the Chrome browser process. Must be called once on application startup."""
        if self._browser:
            return
        async with self._lock:
            if self._browser:
                return
            print(">>> BrowserManager: Starting global Chrome instance...")
            options = ChromiumOptions()
            options.add_argument("--ignore-certificate-errors")
            # You can add options like headless here if needed:
            # options.add_argument("--headless")
            # options.add_argument("--disable-gpu")

            self._browser = Chrome(options=options)
            await self._browser.start()
            print(">>> BrowserManager: Chrome instance started.")

    async def shutdown(self):
        """Shuts down the Chrome browser process. Must be called once on application exit."""
        if not self._browser:
            return
        async with self._lock:
            if not self._browser:
                return
            print(">>> BrowserManager: Shutting down global Chrome instance...")
            # The pydoll Chrome class doesn't have a close() method
            # Instead, we should rely on proper cleanup when the browser object is destroyed
            self._browser = None
            self._pages.clear()
            print(">>> BrowserManager: Chrome instance shut down.")

    async def create_browser_context(self) -> str:
        """Wraps pydoll's create_browser_context."""
        if not self._browser:
            raise RuntimeError("Browser is not started.")
        return await self._browser.create_browser_context()

    async def delete_browser_context(self, context_id: str):
        """Wraps pydoll's delete_browser_context, cleaning up associated pages."""
        if not self._browser:
            # Browser might be shut down during cleanup, which is acceptable.
            return

        # pydoll automatically closes pages when the context is deleted,
        # so we just need to clean up our internal registry.
        # Since we can't easily determine which pages belong to which context,
        # we'll clear all pages when a context is deleted (this is safe since
        # pydoll closes them anyway).
        self._pages.clear()

        await self._browser.delete_browser_context(context_id)
        print(
            f">>> BrowserManager: Deleted context '{context_id[:8]}...' and its pages."
        )

    async def new_tab(self, context_id: str) -> str:
        """Creates a new tab in a given context and returns a unique page ID."""
        if not self._browser:
            raise RuntimeError("Browser is not started.")
        page = await self._browser.new_tab(browser_context_id=context_id)
        page_id = uuid.uuid4().hex
        self._pages[page_id] = page
        return page_id

    def get_page(self, page_id: str) -> Optional[Any]:
        """Retrieves a pydoll page object from our internal registry."""
        return self._pages.get(page_id)


# 1c. The Public API Wrapper
# This is the primary object that users and agents will interact with.


class WebBrowser:
    """The high-level API for creating isolated browser sessions."""

    def __init__(self, manager: BrowserManager):
        self._manager = manager

    @contextlib.asynccontextmanager
    async def isolated_session(self) -> AsyncGenerator[None, Any]:
        """
        An async context manager that provides an isolated browser session.
        Each session is like a new, clean incognito window.
        """
        # --- On entering the 'async with' block ---
        context_id = await self._manager.create_browser_context()
        page_id = await self._manager.new_tab(context_id=context_id)

        session_state = BrowserSessionState(
            browser_context_id=context_id,
            active_page_id=page_id,
            all_page_ids=[page_id],
        )

        # Set the state in the context variable for this async task
        token = current_session.set(session_state)
        print(
            f"--- Session started (context: {context_id[:8]}..., page: {page_id[:8]}...) ---"
        )

        try:
            # Yield control to the code inside the 'with' block
            yield
        finally:
            # --- On exiting the 'async with' block ---
            print(f"--- Session ending (context: {context_id[:8]}...) ---")
            await self._manager.delete_browser_context(context_id)
            # Restore the context variable to its previous state
            current_session.reset(token)


# Create the single, global instances
BROWSER_MANAGER = BrowserManager()
WEB_BROWSER = WebBrowser(manager=BROWSER_MANAGER)


# -- Part 2: LLM Agent Tools --
# These functions are designed to be simple and stateless from the caller's
# perspective. They derive all their context from the `current_session` var.


def html_to_markdown(html: str) -> str:
    """A dummy function to represent HTML to Markdown conversion."""
    # In a real implementation, you'd use a library like `markdownify`.
    content = html.strip()
    if len(content) > 300:
        return content[:150] + "\n...\n" + content[-150:]
    return content


async def go_to_url(page_url: str) -> str:
    """
    Navigate in the current browser session to the web page `page_url`.
    Returns a markdown representation of the page's HTML content.
    """
    print(f"  [TOOL] go_to_url called with: {page_url}")
    session = current_session.get()
    if not session:
        raise RuntimeError("This tool can only be used inside an `isolated_session`.")

    page = BROWSER_MANAGER.get_page(session.active_page_id)
    if not page:
        raise RuntimeError(f"Could not find active page for session.")

    await page.go_to(page_url)
    html = await page.page_source

    return html_to_markdown(html)


async def get_current_page_source() -> str:
    """
    Get the HTML content of the current page in the browser session.
    Returns a markdown representation of the page's HTML content.
    """
    print("  [TOOL] get_current_page_source called")
    session = current_session.get()
    if not session:
        raise RuntimeError("This tool can only be used inside an `isolated_session`.")

    page = BROWSER_MANAGER.get_page(session.active_page_id)
    if not page:
        raise RuntimeError(f"Could not find active page for session.")

    html = await page.page_source
    return html_to_markdown(html)


# -- Part 3: Demonstration --


async def agent_task_one():
    """Simulates an agent finding a jazz pianist."""
    print("\n[AGENT 1] Starting task: Find a jazz pianist.")
    # This agent gets its own isolated browser context
    async with WEB_BROWSER.isolated_session():
        # The agent's tool calls are simple and don't need session IDs
        summary = await go_to_url("https://en.wikipedia.org/wiki/Jazz")
        print(f"[AGENT 1] Navigated to Jazz page. Summary:\n{summary}\n")

        await asyncio.sleep(2)  # Simulate thinking

        summary = await go_to_url("https://en.wikipedia.org/wiki/Herbie_Hancock")
        print(f"[AGENT 1] Navigated to Herbie Hancock. Summary:\n{summary}\n")

    print("[AGENT 1] Task finished. Session closed.")


async def agent_task_two():
    """Simulates an agent researching game theory."""
    print("\n[AGENT 2] Starting task: Research game theory.")
    # This agent gets a *different* and completely separate browser context
    async with WEB_BROWSER.isolated_session():
        summary = await go_to_url("https://en.wikipedia.org/wiki/Game_theory")
        print(f"[AGENT 2] Navigated to Game Theory. Summary:\n{summary}\n")

        await asyncio.sleep(3)  # Simulate thinking

        # Let's prove we have no access to Agent 1's history or cookies.
        # We can ask for the current page source again.
        source = await get_current_page_source()
        print(f"[AGENT 2] Confirming current page is still Game Theory:\n{source}\n")

    print("[AGENT 2] Task finished. Session closed.")


async def main():
    """Main function to run the browser and the agent tasks."""
    try:
        # Start the global browser manager
        await BROWSER_MANAGER.start()

        # Run two agent tasks concurrently. Thanks to our architecture,
        # they will not interfere with each other's browser state.
        await asyncio.gather(
            agent_task_one(),
            agent_task_two(),
        )

    finally:
        # Ensure the browser is always shut down
        await BROWSER_MANAGER.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
