"""Global application static values"""

from collections import NamedTuple
from enum import StrEnum


class AgentLibrary(StrEnum):
    """Python AI Agent Library."""

    ATOMIC_AGENTS = "Atomic Agents"
    AUTOGEN = ("AutoGEN",)
    JOE_HANDROLLED_V1 = "Joe Handrolled v1"
    LANG_CHAIN = "LangChain"
    LANG_GRAPH = "LangGraph"
    OPENAI_AGENTS_SDK = "OpenAI Agents SDK"
    PYDANTIC_AI = "Pydantic AI"
    SMOL_AGENTS = "Smol Agents"
    STRANDS = "Strands"


class AgentBenchmark(NamedTuple):
    """A benchmark dataset for evaluating AI agent performance."""

    name: str
    sample_frac: float
    url: str


benchmarks: tuple[AgentBenchmark, ...] = (
    AgentBenchmark("WebShop", 1.0, "https://webshop-pnlp.github.io/"),
    AgentBenchmark("WebShop", 1.0, "https://webshop-pnlp.github.io/"),
)
