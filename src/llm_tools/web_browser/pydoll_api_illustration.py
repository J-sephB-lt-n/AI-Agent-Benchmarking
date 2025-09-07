import asyncio
from pydoll.browser.chromium import Chrome
from pydoll.browser.options import ChromiumOptions


async def main():
    options = ChromiumOptions()
    options.add_argument("--ignore-certificate-errors")
    async with Chrome(options=options) as browser:
        await browser.start()

        # Create two separate, isolated browser contexts.
        # Each context is like a new, clean incognito window.
        context_one_id = await browser.create_browser_context()
        context_two_id = await browser.create_browser_context()

        # Create a page (tab) within each respective context.
        page_one = await browser.new_tab(browser_context_id=context_one_id)
        page_two = await browser.new_tab(browser_context_id=context_two_id)

        # Now, page_one and page_two are completely isolated
        # and will NOT share cookies or session storage.
        await asyncio.gather(
            page_one.go_to("https://api.my-ip.io/ip"),
            page_two.go_to("https://httpbin.org/cookies"),
        )

        # ... perform independent actions on each page ...
        for page_num, page in enumerate((page_one, page_two), start=1):
            html: str = await page.page_source
            print(f"Starting html of page {page_num}:")
            print(html)
        print("Pages loaded. Waiting for 10 seconds...")
        await asyncio.sleep(10)

        # It's good practice to close the contexts when done.
        await browser.delete_browser_context(context_one_id)
        await browser.delete_browser_context(context_two_id)


asyncio.run(main())
