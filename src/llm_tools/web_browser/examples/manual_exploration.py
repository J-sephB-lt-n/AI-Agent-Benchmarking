"""
Examples of things you can do in the (pdb) interactive console:
- asyncio.get_event_loop().run_until_complete(go_to_url("https://www.google.com"))
"""

import asyncio
from src.llm_tools.web_browser import BrowserManager, WebBrowser, go_to_url


async def main():
    browser_manager = BrowserManager()
    await browser_manager.start_browser(
        browser_args=["--ignore-certificate-errors"],
    )
    try:
        browser = WebBrowser(browser_manager)
        async with browser.isolated_browser_session():
            breakpoint()
    finally:
        await browser_manager.shutdown_browser()


if __name__ == "__main__":
    asyncio.run(main())
