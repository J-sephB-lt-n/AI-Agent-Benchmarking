"""
This module provides a high-level API for AI agents to interact with their isolated browser environments.
"""

from typing import Dict

from .agent_browser import AgentBrowser

_agent_browsers: Dict[str, AgentBrowser] = {}


def _get_agent_browser(agent_id: str) -> AgentBrowser:
    """
    Retrieves or creates an AgentBrowser instance for a given agent ID.
    """
    if agent_id not in _agent_browsers:
        _agent_browsers[agent_id] = AgentBrowser(agent_id)
    return _agent_browsers[agent_id]


async def go_to_url(agent_id: str, url: str) -> str:
    """
    Navigates to a URL in a new page for the specified agent.
    Returns the content of the page.
    """
    agent_browser = _get_agent_browser(agent_id)
    page = await agent_browser.new_page()
    await page.go_to(url)
    content = await page.content()
    return content


async def get_page_content(agent_id: str, page_id: str) -> str:
    """
    Retrieves the HTML content of a specific page for an agent.
    Note: This is a simplified example. In a real implementation, you'd
    have a more robust way of managing and selecting pages.
    """
    agent_browser = _get_agent_browser(agent_id)
    # This assumes the agent has a way to know the page_id.
    # For simplicity, we'll just get the content of the first page.
    if agent_browser._pages:
        page = list(agent_browser._pages.values())[0]
        return await page.content()
    return "No active pages."


async def refresh_browser_context(agent_id: str) -> str:
    """
    Refreshes the browser context for the specified agent, clearing all cookies,
    history, and local storage.
    """
    agent_browser = _get_agent_browser(agent_id)
    await agent_browser.refresh_context()
    return f"Browser context for agent '{agent_id}' has been refreshed."


async def cleanup_agent_browser(agent_id: str) -> None:
    """
    Cleans up and closes the browser context for a specific agent.
    """
    if agent_id in _agent_browsers:
        agent_browser = _agent_browsers[agent_id]
        await agent_browser.close()
        del _agent_browsers[agent_id]
