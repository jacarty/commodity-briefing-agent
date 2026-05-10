# STEP-02 — Environment setup and first model call

## What I did

- Installed `uv` (first time using it instead of `pip` + `venv`).
- Initialised the project in-place with `uv init --python 3.12`.
- Added runtime dependencies: `langchain`, `langgraph`, `langchain-anthropic`,
  `langsmith`, `python-dotenv`, `yfinance`.
- Added dev dependencies: `pytest`, `ruff`.
- Set up `.env` with `ANTHROPIC_API_KEY`. Confirmed `.env` is gitignored.
- Wrote a minimal `scratch.py` that calls Claude Haiku via `ChatAnthropic`
  and prints the response. Got a half-decent joke about commodities trading
  out of it.
- Tested with two consecutive `.invoke()` calls without passing history,
  to confirm the model is stateless between calls.

## What I learned

`pyproject.toml` is the project description; `uv.lock` is the resolved
dependency tree. They cooperate: `pyproject.toml` says "I depend on at
least these versions"; `uv.lock` pins everything to exact versions for
reproducibility. Commit both.

Asking for 8 packages (6 runtime + 2 dev) installed 138 directories in
`site-packages`. The lockfile is 1478 lines. The 130-odd transitive
dependencies are the reason the lockfile matters — without it, "install
LangChain" means "install the latest compatible version of 130+ packages,
hopefully resolving to a working set."

The LangChain package layout is non-obvious but logical:
- `langchain` and `langgraph` for the framework
- `langchain-core` is foundational, pulled in transitively
- Providers are separate: `langchain-anthropic`, `langchain-aws`,
  `langchain-google-genai`. You install only what you use.
- `langsmith` is the standalone observability package.
- `langgraph-sdk` is the *client* for hosted LangGraph deployments — not
  the framework. Easy to confuse.

The hello world taught me the model layer fundamentals:
- `ChatAnthropic` wraps the `anthropic` SDK in LangChain's standard
  `ChatModel` interface. Same interface across all providers, which is the
  whole point.
- Conversations are lists of message *objects* (`HumanMessage`,
  `AIMessage`, `SystemMessage`, `ToolMessage`), not dicts. The dict form
  you see in quickstarts is sugar that LangChain converts internally.
- Every Runnable (models, agents, graphs, tools) has `.invoke()`. The
  interface consistency is real.
- Models read credentials from environment variables by convention.
  `ChatAnthropic` doesn't need an explicit `api_key=` arg if
  `ANTHROPIC_API_KEY` is set.
- **Models are stateless between calls.** Each `.invoke()` is a fresh
  HTTPS request with whatever message list you hand it. If you want
  multi-turn conversation, you maintain the message list yourself —
  appending the AI response, then the next human message, then invoking
  with the full history.

That last point is the conceptual seed for LangGraph: state is something
you carry, not something the model holds. The State object in a graph is
exactly the structure that holds message history (and other things) across
nodes.

## What surprised me

- `uv` is fast in a way that feels almost rude after years of `pip`. Resolves
  and installs in seconds.
- The framework is determined to make you think in messages and runnables.
  Resisting and using dicts works but you'll fight the framework forever.
- Most of the LangChain quickstarts push `create_agent` first, but starting
  there hides the model layer. Going low-level first means I know what
  `create_agent` is built on.

## Open questions

- When does prompt caching kick in for Claude on Anthropic-direct vs the
  cloud variants? Will it just happen via LangChain or do I need to
  configure it?
- The `model="claude-haiku-4-5"` string — how does LangChain parse
  provider-prefixed strings like `"anthropic:claude-haiku-4-5"` that I've
  seen in `create_agent` quickstarts? Is that resolution a `langchain-core`
  thing?
- For the briefing agent, will I be passing a full message history through
  state, or storing structured data and only generating messages at certain
  nodes? Probably the latter, but worth confirming when we design state.

## Glossary

- **uv** — Modern Python package manager and project tool. Replaces pip,
  venv, virtualenv, pip-tools, and pyenv in one binary.
- **`pyproject.toml`** — Standardised Python project file. Holds metadata,
  dependencies, tool configs.
- **`uv.lock`** — Resolved exact-version lockfile for reproducibility.
  Commit to git.
- **Runnable** — LangChain's core protocol. Anything with `.invoke()`,
  `.stream()`, `.batch()` methods. Models, chains, agents, graphs, tools
  are all Runnables.
- **`ChatAnthropic`** — LangChain's wrapper around the Anthropic SDK.
  Implements the standard `ChatModel` interface.
- **Message types** — `HumanMessage`, `AIMessage`, `SystemMessage`,
  `ToolMessage`. The actual classes for messages in a conversation.
- **Statelessness** — Each model `.invoke()` is independent. No memory
  between calls. State (including conversation history) is the caller's
  problem to maintain.
