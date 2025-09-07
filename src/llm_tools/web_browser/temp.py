import asyncio

from pydoll.browser import Chrome
from pydoll.constants import Key


async def google_search(query: str):
    async with Chrome() as browser:
        tab = await browser.start()
        await tab.go_to("https://www.google.com")
        html: str = await tab.page_source
        print(html[:999])


asyncio.run(google_search("pydoll python"))
