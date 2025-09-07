The [pydoll](https://github.com/autoscrape-labs/pydoll) python library uses the following syntax:

```python
@pydoll_api_illustration.py
```

I want to wrap this library inside python functions which can be passed to chat completion and AI agent libraries like this:

```python
# langchain tool-calling example
from langchain_core.tools import tool

@tool
def start_browser_session() -> bool:
    """Start a new isolated browser session."""
    ...

@tool
def go_to_url(page_url: str) -> bool:
    """Navigate in the current browser session to the web page `page_url`."""
    ...

tools = [start_browser_session, go_to_url]
model_with_tools = model.bind_tools(tools)
response = model_with_tools.invoke("Please summarise the page https://en.wikipedia.org/wiki/Game_theory.")
```
