"""
An example script demonstrating how to use the web browser tools for AI agents.
"""

import asyncio

from .. import (
    cleanup_agent_browser,
    get_browser_manager,
    go_to_url,
    refresh_browser_context,
)


async def agent_task(agent_id: str, url: str):
    """Simulates a task for a single AI agent."""
    print(f"[{agent_id}] Starting task: Navigating to {url}")
    initial_content = await go_to_url(agent_id, url)
    print(
        f"[{agent_id}] Navigated to {url}. Page content length: {len(initial_content)}"
    )

    # Simulate some browsing activity
    await asyncio.sleep(2)

    print(f"[{agent_id}] Refreshing browser context.")
    refresh_message = await refresh_browser_context(agent_id)
    print(f"[{agent_id}] {refresh_message}")

    # After refreshing, the agent will have a clean slate (no cookies, etc.)
    # Let's navigate to another page to show the new context works.
    new_url = "https://httpbin.org/headers"
    print(f"[{agent_id}] Navigating to {new_url} in the new context.")
    new_content = await go_to_url(agent_id, new_url)
    print(
        f"[{agent_id}] Navigated to {new_url}. Page content length: {len(new_content)}"
    )


async def main():
    """
    Main function to run the simulation.
    """
    # Define tasks for two different agents
    agent_one_id = "agent_001"
    agent_two_id = "agent_002"

    task1 = agent_task(agent_one_id, "https://api.my-ip.io/ip")
    task2 = agent_task(
        agent_two_id, "https://httpbin.org/cookies/set?name=example&value=123"
    )

    # Run the tasks concurrently
    await asyncio.gather(task1, task2)

    # Cleanup
    browser_manager = await get_browser_manager()
    await browser_manager.stop()
    await cleanup_agent_browser(agent_one_id)
    await cleanup_agent_browser(agent_two_id)
    print("All agent tasks completed and browser cleaned up.")


if __name__ == "__main__":
    asyncio.run(main())
