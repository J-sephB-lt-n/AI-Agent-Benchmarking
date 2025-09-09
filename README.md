# AI Agent Benchmarking

## Available Tools

### Web Browser

```python
uv run python -m src.llm_tools.web_browser.examples.openai
```

## Notes

Desired agent characteristics:

- low cost (and cost tracking)
- speed/efficiency (both time and tokens)
- context management
- memory management
- robustness (code doesn't crash halfway)
- agent permission handling (handoff to user)
- recovery/self-healing (doesn't go round in circles)
- knowledge integration (e.g. RAG, database access tools etc.)
- planning
- nice UI (user can understand what it's doing)
- transparency/explainability
- agent initiative
- doesn't blow things up
- ease of use (difficulty to integrate. Is the agent code writable/readable)
- flexibility (of the implementation API)
- tracing/logging
