# STEP-01 — Orientation and project framing

## What I did

- Decided the shape of the project: a daily commodity briefing agent built
  on LangGraph, deployed three ways for comparison (Claude direct,
  Bedrock+AgentCore, Vertex+Agent Engine with Gemini swapped in for the
  third because I don't have Claude on Vertex).
- Picked crude oil as the Phase 1 commodity — best balance of public data
  availability and news flow.
- Updated `README.md` and `CLAUDE.md` from the template-repo defaults to
  describe this specific project.
- Confirmed the tutorial structure: step-by-step, granular, with a written
  trail in `docs/tutorial/`.

## What I learned

The LangChain ecosystem is three layers and the layers do genuinely
different things:

- **LangGraph** is the runtime — graphs, nodes, edges, state, durability.
  Can be used standalone.
- **LangChain** (the library) sits on top of LangGraph and provides
  high-level abstractions like `create_agent` plus integrations with model
  providers.
- **LangSmith** is the paid observability layer. Framework-agnostic.

The practical rule: start with `create_agent` for any standard tool-calling
agent; drop down to a custom `StateGraph` when you need explicit state,
parallel fan-out, conditional routing, or multi-agent patterns. For this
project we'll do both — the main graph is custom because the
planner/researcher/critic structure needs explicit routing, but the
researcher node will use `create_agent` internally because it's just a
tool-calling loop.

A "graph" in LangGraph terms is just three things: a state object (a
TypedDict, must be a TypedDict in 1.0), nodes (Python functions that read
and update state), and edges (normal or conditional). The conditional edge
is what turns a pipeline into an agent — it's how the graph can loop or
branch based on what's happened so far.

## What surprised me

LangChain hit 1.0 in October 2025 with a commitment to no breaking changes
until 2.0. That's relatively recent — most tutorials still online use the
deprecated 0.x API patterns (e.g. `set_entry_point`, `create_react_agent`
without the new agent abstractions). When Googling later, sort by date.

## Open questions

- How do conditional edges actually work mechanically — is the routing
  function a node, or something else?
- Where does middleware sit in the graph? (Mentioned but not yet seen.)
- When do I use `create_agent` vs `StateGraph` in marginal cases?

## Glossary

- **LangGraph** — Low-level orchestration framework. Provides the graph
  runtime: nodes, edges, state, durability, checkpointing.
- **LangChain (library)** — Higher-level abstractions on top of LangGraph.
  Includes `create_agent` and provider integrations.
- **LangSmith** — Observability and evaluation platform. Framework-agnostic.
- **Graph** — A state object plus nodes plus edges. The whole agent.
- **Node** — A Python function that takes state, returns state updates.
- **Edge** — Connection between nodes. Can be conditional (route based on
  state) or normal (always go to the same next node).
- **State** — A TypedDict holding everything the graph knows during a run.
  In LangGraph 1.0, must be TypedDict, not Pydantic or dataclass.
