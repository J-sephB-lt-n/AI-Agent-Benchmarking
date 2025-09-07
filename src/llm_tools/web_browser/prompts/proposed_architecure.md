### The Core Challenge

The primary challenge is managing state. An LLM agent tool, like `go_to_url(page_url: str)`, is inherently stateless in its definition. However, a web browser is stateful: it has a current page, cookies, and a session history.

Your goal is to bridge this gap: provide a "current" and "isolated" browser session to a sequence of tool calls *without* forcing the tool definitions to be cluttered with state-management parameters (like `session_id`). The session's existence should be implicitly managed by the surrounding context.

Your proposed `async with web_browser.isolated_session():` is the perfect entry point for this implicit management.

### Architectural Blueprint

We will design a system with three main conceptual layers:

1.  **The Singleton Browser Manager:** A long-lived, application-wide object that manages the single, underlying `pydoll` Chrome process.
2.  **The Public API Wrapper (`WebBrowser`):** The object that users and agents interact with. It exposes the `isolated_session()` context manager.
3.  **The Session Context (`contextvars`):** The "magic" that makes the stateless tool functions aware of the current session state without explicit parameter passing.

---

### 1. The Singleton Browser Manager (`BrowserManager`)

This is the low-level, internal engine. It has one core responsibility: to manage the expensive `pydoll.browser.chromium.Chrome` resource.

*   **Lifecycle:** It is created once when the application starts. It launches the `Chrome` process and keeps it running. It has a `shutdown` method to gracefully close the browser when the entire application exits. This avoids the costly overhead of starting and stopping a new browser for every agent task.
*   **Responsibilities:**
    *   Instantiate and hold the single `pydoll` `Chrome` object.
    *   Provide internal, thread-safe methods that map directly to `pydoll` operations:
        *   `create_browser_context()` -> returns a new `context_id`.
        *   `delete_browser_context(context_id)`.
        *   `create_new_tab(context_id)` -> returns a `page_id` and the `pydoll` page object.
        *   `get_page_object(page_id)` -> returns the `pydoll` page object associated with an ID.
        *   `close_page(page_id)`.
    *   It maintains an internal registry mapping `context_id` and `page_id` strings to their corresponding live `pydoll` objects. This is crucial for translating simple IDs back into actionable objects.

### 2. The Public API Wrapper (`WebBrowser`)

This is the high-level, user-facing object. An instance of this would be your `web_browser` variable.

*   **Composition:** It holds a reference to the singleton `BrowserManager`.
*   **Primary Feature: `isolated_session()`:**
    *   This method returns an **asynchronous context manager** object.
    *   **On `__aenter__` (entering the `with` block):**
        1.  It calls the `BrowserManager` to create a new, isolated browser context, receiving a `context_id`.
        2.  It then calls the `BrowserManager` to create an initial page (tab) within that new context, receiving a `page_id`.
        3.  It bundles this information (`context_id`, `current_page_id`, a list of all `page_ids` in the session) into a simple "Session State" object.
        4.  It **sets this Session State object into a `contextvars.ContextVar`**. This is the most critical step. `contextvars` are designed for `asyncio` to carry state along a single task's execution path without explicit passing.
    *   **On `__aexit__` (exiting the `with` block):**
        1.  It retrieves the `context_id` from the Session State stored in the `contextvar`.
        2.  It calls the `BrowserManager`'s `delete_browser_context(context_id)` method. The manager is responsible for cleaning up all associated pages and resources.
        3.  It resets the `contextvar` to its previous state, ensuring no state leaks outside the `with` block.

### 3. The Session Context and The Tools

This layer explains how the simple tool functions work.

*   **The "Magic" of `contextvars`:**
    *   We define a global `contextvars.ContextVar` (e.g., `current_browser_session`).
    *   When code is executed inside the `async with web_browser.isolated_session():` block, any call to `current_browser_session.get()` will return the specific Session State object created for that block.
    *   This is completely isolated. If two different agent tasks run in parallel, each within its own `isolated_session` block, they will each have their own independent Session State in their respective `contextvar`.

*   **Designing the Tools (e.g., `go_to_url`):**
    *   The tool function maintains its simple, LLM-friendly signature: `go_to_url(page_url: str)`.
    *   **Inside the function:**
        1.  It first retrieves the current session's state: `session_state = current_browser_session.get()`. This call will fail if the tool is used outside of an `isolated_session` block, which is a desirable safety feature.
        2.  It gets the ID of the active page: `page_id = session_state['current_page_id']`.
        3.  It gets the `BrowserManager` singleton instance.
        4.  It calls the manager's method to get the actual `pydoll` page object: `page_object = browser_manager.get_page_object(page_id)`.
        5.  It performs the browser action: `await page_object.go_to(page_url)`.
        6.  It retrieves the result: `html = await page_object.page_source`.
        7.  It processes and returns the final output (e.g., `html_to_markdown(html)`).

### Flow of Operations (Summary)

1.  **App Start:** A single `BrowserManager` is created, launching one `Chrome` process. A `WebBrowser` API object is also created.
2.  **Task Start:** An agent task begins, entering an `async with web_browser.isolated_session():` block.
3.  **Session Creation:** The `WebBrowser` object asks the `BrowserManager` to create a new `pydoll` context and an initial page. The IDs are stored in a `contextvar`.
4.  **Tool Call:** The LLM calls `go_to_url(...)`.
5.  **State Retrieval:** The tool function looks up the current `page_id` from the `contextvar`.
6.  **Execution:** The tool uses the `page_id` to ask the `BrowserManager` for the correct `pydoll` page object and executes the command.
7.  **Task End:** The `with` block finishes. The `WebBrowser` tells the `BrowserManager` to delete the `pydoll` context associated with the session. The `contextvar` is cleaned up.
8.  **App End:** A shutdown hook calls `BrowserManager.shutdown()` to close the `Chrome` process.

### Benefits of this Architecture

*   **Elegance:** The tool definitions remain perfectly clean and stateless, as requested. All state management is handled implicitly by the context manager.
*   **Robust Isolation:** Each `isolated_session` is backed by a `pydoll` Browser Context, guaranteeing that cookies, local storage, and sessions are not shared between agent tasks. `contextvars` ensures that the state management itself is also isolated per asynchronous task.
*   **Efficiency:** By using a single, long-lived `Chrome` process, you eliminate the significant performance penalty of browser startup/shutdown for each task. Creating and deleting browser contexts is extremely fast and lightweight.
*   **Extensibility:** This model is easily extended. You can add more tools like `click(selector)`, `get_html()`, `scroll(direction)`, `new_tab()`, or `switch_tab(tab_number)`. The `new_tab` and `switch_tab` tools would simply modify the Session State object held within the `contextvar`.