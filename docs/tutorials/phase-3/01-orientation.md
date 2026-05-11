# STEP-01 — Orientation

Phase 3 builds the same conceptual agent as Phase 1 (LangGraph
direct) and Phase 2 (Strands on Bedrock), this time on Google
Cloud's agent platform with Gemini as the model. The goal isn't
strict portability — it's to build *idiomatically* on whatever
Vertex offers and document where the idioms diverge.

This step is orientation. Before any code, what is this platform,
what are its primitives, and what does an idiomatic agent look
like on it?

## What I did

I asked Claude to read the current Google Cloud docs and summarise.
Reading happened before any code or environment setup — the
intent was to absorb the platform vocabulary, not to follow a
quickstart.

## The platform's name (and what to call it)

The most immediately confusing thing about Phase 3 is that **the
platform is being renamed mid-flight**. At Google Cloud Next 2026,
"Vertex AI Agent Builder" was rebranded as **Gemini Enterprise
Agent Platform**. Some docs use the new name, some still say
"Vertex AI Agent Engine" or "Vertex AI Agent Builder", and the
SDK is still the Vertex AI SDK.

For this tutorial series I'll use the names that match what's
actually visible in the SDK and console at build time. Right now
that means **Vertex AI** for the broader platform and **Agent
Engine** for the runtime — those names still appear in the
client-based Python SDK (`agent_engines` module) and that's what
matters in practice.

If/when the SDK renames, the tutorial will too.

## Platform architecture as I currently understand it

The platform splits into several layers. They're independent;
you can use any combination.

### Build-time frameworks

How you write the agent. Several choices, in rough order of
Google-native to third-party:

- **Agent Development Kit (ADK)** — Google's open-source Python
  framework. Model-agnostic but designed Gemini-first. Equivalent
  in role to Strands (Phase 2) and LangGraph (Phase 1) — it's
  the SDK you reach for to build agents.
- **Agent Studio** — low-code visual builder. Not relevant for
  this project; we're code-first.
- **LangChain / LangGraph / LlamaIndex / AG2 / Agent2Agent /
  Custom** — all supported as deployment targets on Agent Engine.

The fact that Google supports LangChain, LangGraph, LlamaIndex,
and custom agents on Agent Engine matters: it means the **runtime
is decoupled from the framework**. We could (in theory) deploy
the Phase 1 LangGraph agent to Vertex Agent Engine unchanged. We
won't — the point of Phase 3 is to build idiomatically using ADK
— but it's worth noting that this platform is more framework-
neutral than Phase 2's Strands+AgentCore Runtime pairing.

### Runtime layer (Agent Engine)

The managed serverless runtime for deployed agents. Conceptually
equivalent to Phase 2's AgentCore Runtime.

Bills on vCPU-hour, memory, and stored sessions/memories. As of
late 2025: $0.0864 per vCPU-hour, $0.0090 per GB-hour, $0.25 per
1,000 stored events. Model tokens billed separately.

Features that are relevant:
- **Sessions** — stores conversation state, scoped to a user.
- **Memory Bank** — persistent long-term memory across sessions.
  Distinct from Sessions; the former is short-term turn-by-turn
  state, the latter is long-term semantic memory the agent can
  retrieve.
- **Code Execution** — sandbox for the agent to run code.
- **Example Store** — few-shot example retrieval, dynamically
  augments prompts.
- **Observability** — OpenTelemetry → Cloud Trace, Cloud Logging,
  Cloud Monitoring.
- **Evaluation service** — generative evaluation framework
  including offline, online, and simulated evaluation modes.

Note the asymmetry with Phase 2: Phase 2's Bedrock + AgentCore
Runtime gave us model access and deployment, but Phase 2's smoke
tests ran locally. Phase 3's Agent Engine is more obviously a
*production runtime* with first-class observability, evaluation,
and memory primitives. Whether we use those for Phase 3 or stay
local-only is a design question (STEP-03).

### Model layer

Gemini is the default but not the only option:

- **Gemini family** (3 Pro, 3.1 Flash, etc.) — Google's models
- **Claude on Vertex** — first-class via Model Garden
- **Llama, DeepSeek, Gemma, others** — also via Model Garden

ADK is model-agnostic. We *choose* Gemini for Phase 3; it's not
mandated by the framework.

### Surrounding services

A list, not a deep dive — these are things to know exist:

- **Model Garden** — catalog of 200+ models
- **RAG Engine** — managed retrieval-augmented generation
- **Vector Search** (and Vector Search 2.0) — vector database
- **Agent Identity / IAM** — every agent has an identity, gets
  policies attached
- **Agent Gateway** — routing/governance layer in front of
  agents
- **Model Armor** — content safety / prompt-injection defense
- **Agent Registry** — catalog of deployed agents

Most of these aren't needed for our commodity briefing agent.
They become relevant at production scale — e.g. you'd put an
agent behind Agent Gateway with Model Armor if it served
external users. For Phase 3's scope (one agent, one workflow,
solo developer), we'll touch at most: ADK, Agent Engine,
Gemini, possibly Sessions and Memory Bank, possibly
observability via Cloud Trace.

## How Phase 3 might compare to Phase 1 and Phase 2

### Build-time: ADK vs Strands vs LangGraph

ADK is conceptually closer to **Strands** than to LangGraph:

- **LangGraph** (Phase 1): explicit graph topology, typed state,
  declarative wiring of nodes and edges. The framework owns
  control flow.
- **Strands** (Phase 2): agents-as-tools pattern; agent loop
  drives, model decides what to call next based on prompt
  instructions. The model owns control flow.
- **ADK** (Phase 3, expected): tool-using agent loop, similar to
  Strands, but with more Google-cloud-native primitives
  (sub-agents, agent-to-agent protocols, structured workflows).

If this picture is right, Phase 3 will look structurally more
like Phase 2 than Phase 1, with platform-specific richness in
the runtime layer.

### Runtime: Agent Engine vs AgentCore vs nothing

Phase 1 had no runtime — agents ran locally and the LangGraph
graph was the unit of deployment.

Phase 2 has AgentCore Runtime in principle, but our actual smoke
tests ran locally via SSO. Deployment was deferred.

Phase 3 has Agent Engine front-and-centre. We could continue
the "local-only smoke tests" pattern, or we could actually
deploy. This is a real design decision — Phase 3 is the natural
phase to test deployment if we're going to.

### Memory / Sessions

Phase 1 and 2 had no concept of long-running sessions or
persistent memory. Each invocation was a one-shot brief.

Vertex's Sessions + Memory Bank give us conversation continuity
and long-term memory. **Probably not needed** for the commodity
briefing agent — it's still a daily one-shot job. But if Phase 3's
goal is to be idiomatic on Vertex, this is a primitive worth at
least naming as "deliberately not used, here's why."

### Cost shape

Phase 1: ~$0.30–0.50 per run (Sonnet + Anthropic web search)
Phase 2: ~$0.13 happy-path, ~$0.20–0.25 with retries (Haiku
on Bedrock)

Phase 3 cost is genuinely unknown until we know which Gemini
model we'll use and whether we'll incur Agent Engine runtime
hours. If we run smoke tests locally (no Agent Engine), it's
just Gemini token costs + Tavily. If we deploy to Agent
Engine, vCPU and memory hours add up.

## What I think I want for STEP-03 design

Carrying forward from STEP-01:

1. **ADK is the framework choice.** Even though LangChain /
   LangGraph also deploy to Agent Engine, using them would
   undercut Phase 3's purpose — we'd be testing platform
   neutrality, not Vertex's strengths.
2. **Gemini is the model.** Specifically, probably Gemini 3.1
   Flash for the research/specialist work (cheap, fast) and
   Gemini 3 Pro for synthesis/orchestrator if the cheap-model
   results aren't strong enough. Mirrors the Phase 2 pattern
   (Haiku 4.5 across the board, with Sonnet as fallback option).
3. **Deployment decision is deferred to STEP-03.** Two reasonable
   answers: stay local-only (matches Phase 2), or deploy to
   Agent Engine (tests something Phase 2 didn't). We'll decide
   in design.
4. **Memory Bank is probably not used.** The agent is one-shot
   daily. But worth naming explicitly in design.
5. **Observability via Cloud Trace is probably worth turning on
   even if we run local.** Free, gives us per-tool latency and
   token attribution that Phase 2's streamed-stdout didn't.

## Open questions for STEP-02 and STEP-03

- **Web search.** Phase 1 used Anthropic's server-side web search
  tool. Phase 2 used Tavily (because Anthropic's tool isn't
  available on Bedrock). What does ADK offer? Google Search
  grounding is built into Gemini via Vertex — we could use that
  directly without a third-party search tool. If so, that's a
  cleaner story than Phase 2.
- **Structured output.** Phase 1 used `with_structured_output`.
  Phase 2 used `structured_output_model` once, at the agent
  boundary. What does ADK offer for typed agent outputs? Pydantic
  support, JSON schema enforcement, something else?
- **Multi-agent vs single-agent.** ADK supports "sub-agents" as
  first-class — agents wired into agents. Phase 2's agents-as-tools
  pattern is conceptually similar but architecturally different.
  Worth understanding ADK's sub-agent model before STEP-03 design.
- **The deployment-or-not question.** Resolved in STEP-03.

## Repository-level setup needed (for STEP-02)

The repo layout decision was made in Phase 2's planning:

- `phase3-vertex-gemini/` for the package (matches
  `phase2-strands-bedrock` style, no hyphen)
- `docs/tutorials/phase-3/` for tutorials (matches `phase-1`,
  `phase-2` style, with hyphen)

STEP-02 will cover: GCP project setup (using the existing
`carty-470812` project from earlier GCP ML work), Vertex AI API
enablement, ADK installation via uv, Gemini access, and any
auth-related credential setup.

## What I'm not yet sure about

This is the most "framework-rich" platform of the three. Vertex
has Memory Bank and Sessions and Code Execution and an Evaluation
service and Example Store and Model Garden — five Phase-2-scale
primitives I could theoretically use. The risk is over-engineering
the briefing agent by using primitives because they exist, not
because the agent needs them.

The discipline I want to bring from Phase 2: **use what makes the
agent better, and explicitly say no to the rest.** Phase 2's
retrospective made this clear — the framework is scaffolding,
the prompts are substance. Vertex offers more scaffolding; the
prompts still do the work.
