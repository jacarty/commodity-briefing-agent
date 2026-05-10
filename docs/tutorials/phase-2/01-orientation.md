# STEP-01 — Orientation

Phase 2 starts here. Same agent, different architecture.

The point of the project as a whole is *building the same thing
three ways* — not "running LangChain on three providers." Phase 1
was the LangGraph implementation. Phase 2 is the Strands + Bedrock
AgentCore implementation. Phase 3 will be Vertex Agent Engine with
Gemini.

Phase 2 isn't a port. It's a rebuild on different primitives.

## What carries over from Phase 1

Things that aren't being re-decided:

- **The agent itself** — daily oil briefing, four research streams
  (price, news, catalysts, geopolitics), synthesis, audit, prose
  drafting, audit again, email-shaped delivery
- **The prompts** — copied verbatim from Phase 1, updated only if
  Bedrock-Claude behaviour differs from Anthropic-direct
- **The schemas in spirit** — same field names, same Literal enum
  values, same meaning. The implementing types may not be TypedDict
  any more.
- **The two-stage analyse-then-render split** — analytical work
  (synthesis) separate from rendering (draft), each with its own
  auditor
- **Bounded loops with retry caps** — never trust an LLM-driven
  feedback loop to terminate on its own
- **Auditor pass-bias** — auditors must be told what is *not* a
  flagged issue, or they over-flag

The retrospective for Phase 1 is in
[`../../retrospectives/phase-1-retrospective.md`](../../retrospectives/phase-1-retrospective.md).
The full architectural write-up is in
[`../phase1/13-architecture.md`](../phase1/13-architecture.md).
Both should be considered context for what follows.

## What's different in Phase 2

Three big shifts.

### Framework: Strands instead of LangGraph

Strands is AWS's open-source agent SDK. Model-driven by design —
the framing in their own docs: *"rather than defining complex
workflows for their agents, Strands embraces the capabilities of
state-of-the-art models to plan, chain thoughts, call tools, and
reflect."*

The conceptual unit is `Agent(model, tools, prompt)`. Multiple
patterns built on top of that — single agents with tools,
agents-as-tools (hierarchical delegation), swarm (peer-to-peer),
graph (LangGraph-shaped), workflow (rigid sequences).

Phase 2 uses **agents-as-tools**. One orchestrator agent. Specialist
agents wrapped as `@tool` functions. The orchestrator's prompt
encodes the workflow; calling a specialist looks like calling any
other tool. Hierarchical: orchestrator → specialists. The
orchestrator never gives up control.

This is a genuinely different shape from Phase 1. In LangGraph, the
workflow lived in graph topology — edges, conditional routing,
explicit state transitions. In agents-as-tools, the workflow lives
*in the orchestrator's prompt*, expressed as instructions for when
to call which specialist. The model handles the orchestration.

### Provider: Bedrock instead of Anthropic direct

Same Claude model under the hood, different API surface, different
auth, different infrastructure. AWS credentials replace the Anthropic
API key. Cross-region inference becomes a real consideration.
Per-call costs differ.

The biggest concrete change: Anthropic's server-side
`web_search_20250305` tool isn't available on Bedrock. Phase 1's
research nodes used it directly. Phase 2 needs an alternative —
**Tavily**, called as a Python tool. Tavily isn't worse, but it is
different — it returns ranked results with snippets, and the model
has to reason over them rather than receiving the synthesised search
output Anthropic's tool produces.

### Deployment target: AgentCore Runtime instead of "TBD Lambda"

Phase 1 was always going to deploy to AWS Lambda + SES at some
point, but Phase 1's harness was never built. Phase 2 deploys to
Bedrock AgentCore Runtime — a managed serverless agent host that
sits alongside Bedrock proper.

AgentCore handles session isolation, scaling, observability via
OpenTelemetry. The agent is invoked over HTTP. This shifts how we
think about state — within a run, state is in-memory; across runs,
state lives in AgentCore's session store or external storage we
configure (DynamoDB, etc.).

## What I'm trying to learn from Phase 2

Phase 1 produced patterns that *felt* like principles. State-first
design, schema-as-contract, two-stage analyse-then-render. Phase 2
is where those get tested. Either they survive the agents-as-tools
shape, or they were LangGraph-shaped under the surface.

Specific things I'm watching for:

- **Does the orchestrator's prompt successfully encode the workflow,
  including retry caps?** In Phase 1, retry caps were Python `if`
  statements in router functions. In Phase 2, the orchestrator's
  prompt says "if the auditor flags issues, ask the relevant
  specialist again, but don't loop more than twice." Whether models
  reliably enforce this from a prompt alone is an open question.
- **What happens to "state"?** LangGraph had a `State` TypedDict
  that every node read and wrote. Strands has `invocation_state` for
  graphs; agents-as-tools has function-call argument passing. The
  orchestrator's conversation history acts as state, implicitly. How
  this shapes the design is unknown.
- **How well does the model handle the research-and-audit loop via
  reasoning alone?** In Phase 1, cross-check + re-research was a
  graph cycle with explicit routing. In Phase 2, the orchestrator
  has to *decide* when to re-call a specialist after audit feedback.
  This is the model-driven approach earning its keep.
- **Is Tavily research quality comparable to Anthropic's
  server-side search?** This affects prompts more than architecture,
  but it's worth measuring early.

## The translation problem

Phase 1's 12 nodes don't map 1:1 to Phase 2 components. Some natural
mappings, some genuinely awkward ones — full design discussion comes
in STEP-03, but a rough preview:

**Probably specialist agents** (LLM-driven research and reasoning):
research_news, research_catalysts, research_geo, synthesise,
cross_check, draft, sense_check, revise.

**Probably plain tools** (no LLM): research_price (yfinance fetch).

**Probably absorbed by the orchestrator**: plan (the orchestrator's
prompt and reasoning *is* the plan), re_research (the orchestrator
just calls the relevant specialist again with feedback).

So roughly 8 specialists + 1 plain tool + 1 orchestrator, vs Phase
1's 12 nodes. Different shape. The collapse of `plan` and
`re_research` into the orchestrator is the most interesting
structural change — those nodes existed in Phase 1 because the graph
needed explicit places for that work to happen. In agents-as-tools,
the orchestrator handles both implicitly.

The translation isn't just node-counting. It also covers:
- How specialist agents get their inputs (function arguments vs
  shared state)
- How specialist outputs reach the orchestrator (return values vs
  state updates)
- Where retry caps live (orchestrator prompt vs router functions)
- How the email-shaped delivery format is produced (deliver
  specialist agent vs orchestrator's final response)

## What I'm not deciding right now

A few things deferred to later steps:

- **Environment setup**: AgentCore + Bedrock + IAM + Strands install
  is non-trivial; STEP-02 covers it
- **The full design**: which agents, which tools, what the
  orchestrator's prompt looks like — STEP-03
- **Specific code patterns**: structured output via Strands,
  Pydantic models, tool decorators — emerge as we build

## What's already settled

For reference, choices made before this step started:

- **Pattern**: agents-as-tools (decided after considering
  single-agent, agents-as-tools, swarm, graph, workflow)
- **Web search**: Tavily
- **Deployment**: AgentCore Runtime
- **Model**: Claude via Bedrock (same model family as Phase 1, on
  Bedrock infrastructure)
- **Repo location**: `phase2-strands-bedrock/` as a sibling to
  `phase1-langgraph/`
- **Prompts**: copied verbatim from Phase 1, adjusted only if
  Bedrock-Claude needs different wording

## What surprised me

- That the patterns Phase 1 felt confident about — state-first,
  two-stage, graph-shaped control flow — might all need to be
  rethought for the new framework. The retrospective named them as
  "provisional pending Phase 2/3" but I underestimated how
  provisional.

- How much of the agent's behaviour is going to live in *the
  orchestrator's prompt* in Phase 2. In Phase 1, prompts were
  per-node. In Phase 2, the orchestrator's prompt becomes the
  workflow specification. That's a big shift in where "the design"
  physically lives.

- That moving off Anthropic's server-side `web_search` and onto
  Tavily isn't a downgrade — it's a different research idiom. The
  prompts may need to change to match.

## Open questions

- Will the orchestrator reliably enforce retry caps from prompt
  instructions alone, or will we need to fall back to programmatic
  caps?
- Will any specialist need its own bound tools (Tavily for the
  research specialists, presumably), or will all tool use route
  through the orchestrator?
- Does AgentCore Runtime impose constraints on agent shape that
  affect the design? (E.g., session timeout limits, stateful vs
  stateless invocation patterns.)
- Where does configuration live? Phase 1 used `.env` for the
  Anthropic key. Phase 2 needs AWS credentials — local dev via
  `~/.aws/credentials`, deployed via IAM roles. Different model.

## Glossary

- **Agents-as-tools** — Strands pattern where one orchestrator agent
  treats specialist agents as callable tools. Hierarchical
  delegation. The orchestrator's prompt encodes the workflow.
- **Strands Agents** — AWS-built open-source agent SDK. Model-driven
  by design; supports single-agent, agents-as-tools, swarm, graph,
  and workflow patterns.
- **AgentCore Runtime** — AWS-managed serverless agent host. Sits
  alongside Bedrock. Framework-agnostic (works with Strands,
  LangGraph, custom code) but designed with Strands in mind.
- **Tavily** — Web search API designed for LLM use. Returns ranked
  results with snippets. Replaces Anthropic's server-side
  `web_search_20250305` for Phase 2.
- **Model-driven orchestration** — Workflow logic encoded in the
  model's prompts and reasoning, rather than in explicit graph
  topology. Strands' default approach. The opposite of how Phase 1
  worked.
