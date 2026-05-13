# Phase 3 retrospective

Phase 3 is complete. Local pipeline works (129s end-to-end);
deployed pipeline works (141s end-to-end on Agent Engine);
FinalBrief produced reliably; all seven STEP-03 questions
answered.

## What Phase 3 built

The same conceptual agent as Phases 1 and 2 — research →
synthesise → audit → draft → audit → deliver — built
idiomatically on ADK + Vertex AI + Gemini 2.5 Flash, deployed to
Agent Engine.

The agent has:

- 8 specialist agents: research_news, research_catalysts,
  research_geo, synthesise, cross_check, draft, sense_check,
  revise (where synthesise has initial + revise variants)
- 1 final assembly agent: final_brief (with
  `output_schema=FinalBrief`)
- 3 workflow agents: ParallelAgent for research, LoopAgent for
  synthesis audit, LoopAgent for rendering audit
- 1 custom BaseAgent orchestrator coordinating all stages
- 2 tools: `fetch_price` (direct call, no LLM), `exit_loop`
  (auditor signal)
- 1 Pydantic model: `FinalBrief`
- 1 deployed Agent Engine resource on Vertex AI

Total: 23 Python source files, 9 markdown prompts, ~1500 lines
of code.

## STEP-03 open questions — final scoreboard

| Question | Answer |
|---|---|
| Prompt-port-verbatim for Gemini | ✅ Six of seven prompts ported verbatim (cross_check and sense_check needed a minimal exit_loop footer; the rest were unchanged). Phase 2's "prompt-level discipline is the portable layer" lesson held strongly. |
| `google_search` quality vs Tavily | ✅ Competitive on content. Vertex grounding URLs are click-tracked redirects rather than direct publisher URLs; the `Source` field carries human-readable attribution. |
| `ParallelAgent` parallelises | ✅ Three concurrent research streams complete in roughly the time of one (18.2s vs ~20-40s individually). |
| `exit_loop` reliability | ✅ Held cleanly across both audit loops in all smokes (local and deployed). The alternating-but-not-exiting bug pattern from GitHub issues #2988/#2692 didn't manifest for our text-output-with-single-tool auditor pattern. |
| Gemini's PASS-with-notes calibration | ⚠️ Held for isolated cross_check tests on toy inputs; on real-pipeline inputs both auditors lean strict and frequently hit iteration 2. |
| `event.actions.escalate = False` suppression | ✅ Validated PR 5 — pipeline continued past both loops cleanly in both local and deployed smokes. |
| `output_schema=FinalBrief` reliability | ✅ Produced valid `FinalBrief` on first try in every smoke run (4 total). The retry path (defence-in-depth for ValidationError) did not fire. |

## STEP-03's deferred design question

> *"Does revise stay surgical or full-rewrite the draft?"*

**Answer: revise is not surgical on Gemini Flash.** Same prompt
as Phase 2 ("targeted revision, not a rewrite"). Gemini fixes
the flagged issues but the output reads like a fresh rendering
from the synthesis rather than a targeted edit of the bad draft.
The final brief is correct; the surgical-edit behaviour the
prompt requests isn't what Gemini delivers.

Open: whether this is a model-level difference vs Haiku, a
prompt-tuning issue, or something specific to ADK's handling.
Worth investigating in the cross-phase comparison.

## Phase 3-specific findings (not asked in STEP-03 but worth carrying forward)

### Finding: state writes from custom BaseAgent need state_delta

The first version of PhaseThreeOrchestrator wrote
`state["price_data"]` via direct `ctx.session.state[key] = value`
assignment. The smoke ran end-to-end and synthesise produced
correctly-grounded output. But the final state inspection showed
`price_data: (missing)`. Direct state assignment from custom
agents writes the in-memory state dict (which downstream agents
in the same invocation see) but isn't persisted into the
canonical session state by the SessionService.

The fix: yield an Event with `EventActions(state_delta={...})`
to write through the canonical path. Belt-and-braces: also
keep the direct assignment for immediate downstream visibility,
since state_delta is applied async.

This is the kind of ADK gotcha that's hard to find in the docs
but obvious in retrospect. Future custom BaseAgent
implementations should use state_delta.

### Finding: function_call-only PASS responses

When an auditor calls exit_loop on PASS, Gemini outputs ONLY
the function call — no text. `state["cross_check_result"]` is
empty after a PASS. Same applies to sense_check. Detection
must use function_call events, not state parsing.

This was a real surprise from PR 3 that persisted through the
rest of Phase 3. It's consistent with the ADK docs example for
refinement loops ("EITHER call exit_loop OR output text, never
both") — Gemini learned this constraint from training and
applies it cleanly.

### Finding: ParallelAgent event stream is coarse

Only one event per sub-agent (the final response). No
intermediate tool calls visible to the top-level Runner. Good
for orchestrator simplicity; bad for fine-grained observability.

### Finding: auditors lean strict on real pipeline inputs

In all 4 end-to-end runs (2 local + 2 deployed), both audit
loops hit iteration 2. The "bias toward passing" prompt
guidance is taking effect on isolated smoke tests but not as
strongly on real-pipeline inputs where the auditor has more
surface area to evaluate. This is fine — the loop design
absorbs the variance — but it shifts the expected latency
budget upward.

### Finding: large run-to-run latency variance

Two local runs of the same code produced 365s and 129s wall-
clock with the same iteration counts. Variance is real and
large; single-run benchmarking is unreliable. PR 5 documented
this; PR 6 deploy testing showed a similar pattern (141s on
first invocation; subsequent runs may be faster).

### Finding: Agent Engine deploy requires cloudpickle workaround for src/ layout

Agent Engine's `extra_packages` parameter copies files into
the remote container but does not make them importable via
`sys.path`. For projects using a `src/` layout, the remote
container cannot resolve module references baked into the
pickle, producing `ModuleNotFoundError`.

Three approaches were tried and failed: passing the source
directory, passing the project root, and passing a pre-built
wheel file. None resulted in the package being importable in
the remote container.

The fix: `cloudpickle.register_pickle_by_value(briefing_agent)`
before the pickle step. This embeds the full source code into
the pickle itself, making it self-contained. The remote
container never needs to import the module.

This is a known issue — multiple `adk-python` GitHub issues
(#2044, #2947, #3532) document the same `ModuleNotFoundError`
pattern. Google's ADK team recommends building a wheel, but
`register_pickle_by_value` is simpler and works reliably for
our use case.

## Cross-phase comparison

What Phase 3 changed vs Phase 2:

### Architecture

| Aspect | Phase 2 (Strands+Bedrock) | Phase 3 (ADK+Vertex) |
|---|---|---|
| Orchestrator | LlmAgent with declarative-goal prompt | Custom BaseAgent subclass with explicit control flow |
| Specialist coordination | Agents-as-tools (orchestrator calls specialists as tools) | Workflow agents (ParallelAgent, LoopAgent) + direct sub_agent.run_async |
| Inter-agent data | Concatenated input strings | session.state + `{key}` template substitution |
| Audit routing | Text-parsing the "VERDICT: PASS" line | Function call (exit_loop → escalate signal) |
| Audit retry | Orchestrator prompt instructed retry loops | LoopAgent with max_iterations cap |
| Parallel research | Sequential (Strands has no parallel primitive) | Concurrent (ParallelAgent) |
| Final brief structure | Pydantic validation via tool result | `output_schema=FinalBrief` enforced by ADK |
| Deploy target | Local | Vertex AI Agent Engine (managed runtime) |

### What ports cleanly

- All seven specialist prompts (six fully verbatim, two with
  small exit_loop footer addition)
- The `PriceSnapshot` dataclass and `fetch_price` body
- The `FinalBrief` Pydantic model (identical fields)
- The fabrication-injection pattern for failure-path smoke tests
- The "bias toward passing" auditor calibration framing
- The bounded-retry + cap-fallback design

### What doesn't port

- The orchestrator (Phase 2's declarative prompt → Phase 3's
  custom BaseAgent code)
- The agents-as-tools pattern (Phase 3 uses sub_agent.run_async
  directly)
- The auditor's PASS rationale (Phase 2 captured it as text in
  state; Phase 3 loses it on PASS)
- Tavily search results (Phase 3 uses first-party google_search)
- Local-only deployment story (Phase 3 deploys to managed runtime)

## Lessons for the cross-phase comparison

Three things worth dwelling on for a future cross-phase write-up:

### Lesson 1: Editorial discipline lives in prompts

Phase 2's retrospective said this. Phase 3 validated it. Six of
seven specialist prompts ported verbatim with no changes; the
seventh (cross_check) needed only a small adaptation for the
function-call routing mechanism. The same prose-output discipline
that worked on Haiku also works on Gemini Flash.

This is the most important and underrated finding across both
phase migrations: when you do the editorial work right, the
prompts carry across frameworks and models.

### Lesson 2: Framework abstraction is a real trade-off

- **Phase 1 (LangGraph):** explicit state graph, explicit edge
  transitions. Verbose but transparent.
- **Phase 2 (Strands):** orchestrator prompt drives everything.
  Compact but opaque.
- **Phase 3 (ADK):** workflow primitives (ParallelAgent,
  LoopAgent) + custom BaseAgent for non-trivial control flow.
  Moderately verbose, quite transparent — but the LoopAgent
  escalate-propagation behaviour and the state_delta
  requirement are framework surprises that don't appear until
  you hit them.

ADK's workflow agents are powerful when your control flow fits
their pattern. The moment it doesn't (two LoopAgents in
sequence, in our case), you fall back to custom BaseAgent and
write Python explicitly. This is fine; it just means "pure
workflow agents" isn't a viable approach for non-trivial
pipelines.

### Lesson 3: Observability is the area where ADK feels least mature

Coarse event streams from workflow agents, empty state keys on
PASS audits, the "Event from an unknown agent" warning when
running specialists across multiple Runners, the state_delta
gotcha for custom agents — none of these are bugs, but they
make debugging harder than Phase 2 was.

For production use beyond this learning project, you'd want
Cloud Trace enabled (we set `enable_tracing=True` at deploy time
but didn't inspect the trace data), per-specialist callback-
based logging, and probably a custom event-aggregator to make
event streams human-readable.

## Deployment story

Agent Engine deploys by pickling the agent object locally and
unpickling it in a managed container. For projects using a
`src/` layout, `cloudpickle.register_pickle_by_value` is
required to embed the source code into the pickle — the remote
container won't have the local package on `sys.path`.

```python
import cloudpickle
import briefing_agent
cloudpickle.register_pickle_by_value(briefing_agent)

vertexai.init(project=..., location=..., staging_bucket=...)
app = agent_engines.AdkApp(agent=orchestrator, enable_tracing=True)
remote_app = agent_engines.create(
    agent_engine=app,
    requirements=[...],
    display_name="commodity-briefing-agent",
)
```

Deploy time: ~3 minutes. First deployed invocation: 141s (vs
129s local). Cold start adds ~10-15s; subsequent invocations
should be closer to local.

The deployed agent is fully equivalent to the local agent —
same code, same prompts, same orchestrator, same FinalBrief
output. The one observed rendering difference (blank line
after section headers in plain_text_body) is an artefact of
Vertex's text serialisation, not a behavioural change.

## What's next

Phase 3 is the third and final implementation of the same agent.
The three-phase comparison is now possible. A cross-phase
comparison post (separate piece of work) would compare:

- Code volume and clarity across the three frameworks
- Where each framework's abstractions help vs hinder
- Cost per run (token spend + framework overhead)
- Observability and debuggability
- Which patterns ported cleanly vs which needed framework-
  specific adaptation
- Cost of deployment (Phase 3 has a real deploy story; Phases
  1 and 2 don't)

That comparison is its own piece of work and deserves separate
thinking. Phase 3 is complete.

## Cleanup

The deployed resource costs per-vCPU-hour while running.
Undeploy before any extended idle period:

```python
import vertexai
from vertexai import agent_engines
vertexai.init(project="carty-470812", location="us-central1")
remote_app = agent_engines.get(
    resource_name="projects/873708835509/locations/us-central1/reasoningEngines/3829216919253155840"
)
remote_app.delete()
```

For now (active development / cross-phase comparison phase),
leave deployed.
