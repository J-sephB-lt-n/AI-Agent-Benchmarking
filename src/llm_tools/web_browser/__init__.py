"""
This package provides tools for AI agents to perform web browsing tasks in isolated environments.
"""

from .browser_manager import get_browser_manager
from .tools import (
    cleanup_agent_browser,
    get_page_content,
    go_to_url,
    refresh_browser_context,
)

__all__ = [
    "go_to_url",
    "get_page_content",
    "refresh_browser_context",
    "cleanup_agent_browser",
    "get_browser_manager",
]
