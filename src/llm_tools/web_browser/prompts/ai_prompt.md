The [pydoll](https://github.com/autoscrape-labs/pydoll) python library uses the following syntax:

```python
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
```

I want to wrap this pydoll usage inside python functions which can be used by LLM chat completion and AI agent libraries like this:

```python
# langchain tool-calling example
from langchain_core.tools import tool

@tool
def go_to_url(page_url: str) -> str:
    """Navigate in the current browser session to the web page `page_url`."""
    ...
    page_html: str = await page.page_source
    return html_to_markdown(page_html)

tools = [go_to_url]
model_with_tools = model.bind_tools(tools)
response = model_with_tools.invoke("Please summarise the web page https://en.wikipedia.org/wiki/Game_theory.")
```

```python
# openai python example
def go_to_url(page_url: str) -> str:
    """Navigate in the current browser session to the web page `page_url`."""
    ...
    page_html: str = await page.page_source
    return html_to_markdown(page_html)
llm_client = openai.OpenAI(
    base_url=os.environ["OPENAI_API_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
)
llm_response = llm_client.chat.completions.create(
    model=os.environ["OPENAI_MODEL_NAME"],
    messages=prompt_messages,
    tools=[func_defn_as_json_schema(go_to_url)],
)
```

I propose that each AI agent gets a persistent and isolated browser session using a context manager `.isolated_session()` like this:

```python
agent = AIAgent()
agent.tools = [go_to_url]
for task in (
    "Please start at web page https://en.wikipedia.org and follow links until you find a jazz pianist.",
    "Please start at web page https://en.wikipedia.org/wiki/Game_theory and see if you can get to https://en.wikipedia.org/wiki/Pentatonic_scale just by following page links."
):
    async with web_browser.isolated_session():
        await agent.run(task=task)
```

Explain how you would architect this in an elegant and robust way without writing any code.

------------------------------------------------------------------------------------------------
(new prompt)

Sticking strictly to the pydoll syntax which I showed you, implement this in python (3.12).