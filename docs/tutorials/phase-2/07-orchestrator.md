# STEP-07 — The orchestrator

The orchestrator is live. It takes a natural-language briefing
request, plans the workflow, calls the eight specialists in the
right order, handles audit failures with retry caps, and produces
a `FinalBrief` as structured output.

This step covers PR 5 — the orchestrator built and validated on
both the happy path and both failure paths.

## What I did

- Built the `FinalBrief` Pydantic model (subject, html_body,
  plain_text_body) — same shape as Phase 1's FinalBrief. The only
  structured-data boundary in the agent; every internal specialist
  returns text.
- Wrote the orchestrator's system prompt as **declarative goal +
  constraints** rather than imperative recipe. Three phases
  (research-and-synthesis, rendering, final output), each with
  audit gates, retry caps stated as hard constraints, fallback
  behaviour specified.
- Built the orchestrator agent factory. Wires every specialist as
  a tool plus `fetch_price`. Streams to stdout by default (no
  `callback_handler=None`) so dev runs show the workflow live.
  `structured_output_model` set per-invocation, not at construction,
  so the model only produces `FinalBrief` on the final turn.
- Wrote three smoke tests:
  - **Happy path** — single invocation, expect both audits to pass.
  - **cross_check failure** — stub auditor always returns
    `VERDICT: FAIL`, verify retry cap holds at 2 cycles.
  - **sense_check failure** — same pattern for the second auditor.
- Logged six observations across the smoke runs in
  `docs/observations.md`.

## What I learned

### Declarative orchestrator prompts work

STEP-03's Q1 named two reasonable orchestrator prompt shapes:
imperative recipe ("first call fetch_price, then research, then...")
vs declarative goal + constraints ("here's the goal, here are the
specialists, here are the rules"). We picked declarative.

The risk was the model planning steps differently than designed.
The reward was a simpler, more flexible orchestrator that lets the
model reason about workflow rather than execute a script.

The bet paid off. The orchestrator narrated its plan at the start
of each run, called specialists in the right order, recognised
audit verdicts correctly, and handled failures with reasoning
rather than mechanical step-counting. The narration is striking
on its own:

> *"I've now reached my retry cap for cross_check (2 cycles
> maximum). The second cross_check has failed, so per workflow
> rules, I must proceed to Phase 2 with the best synthesis
> available."*

And in the sense_check failure run, the model recognised the stub
for what it was:

> *"The sense_check is returning a test stub that always fails (as
> noted in the output). This is a cap-testing scenario."*

That's reasoning about the situation, not pattern-matching the
prompt. Genuinely more sophisticated than I expected.

### Prompt-only retry-cap enforcement is real

This was STEP-03's biggest open question: *"Either the model
reliably enforces 'no more than twice' from prompt instruction, or
it doesn't."*

It does. Both retry loops use the same prompt-only mechanism (a
hard constraint stated in the orchestrator prompt: *"Do not run
this loop more than twice in total. If the second [audit] also
fails, proceed to [next phase] anyway with the best [output]
available."*) and both work under genuine failure conditions.

The model:

- Counts tool-call cycles from its own conversation history
- Stops at exactly 2 when told the cap is 2
- Proceeds to the next phase with the latest output
- Names the cap explicitly in its narration

No `@tool` counter safety net needed. No `Graph` fallback. The
prompt is the specification.

### Selective re-research works

In the cross_check failure run, the orchestrator read
`RE-RESEARCH TARGETS: news` from the stub's output and re-ran
*only* `research_news` in the retry cycle. Catalysts and geo
were preserved unchanged. That's the design's cost-conscious
behaviour (don't re-run all four streams when only one needs
updating) working as intended.

The selectivity matters: rerunning all four research specialists
on every retry would double the cost of the chain. The
RE-RESEARCH TARGETS field on cross_check's output, designed in
PR 3, lets the orchestrator be precise. The orchestrator
correctly used that signal.

### Input-string assembly works without explicit Python helpers

In the smoke tests for synthesise, cross_check, draft, sense_check,
and revise, the assembly logic was Python code (`assemble_*_input`
functions). For the orchestrator, the assembly happens in the
model's reasoning — the prompt shows an example structure with
`=== PRICE DATA ===`, `=== NEWS RESEARCH ===`, etc., and the model
reproduces this pattern when calling downstream specialists.

We have no direct visibility into the strings the orchestrator
builds for synthesise, etc. But the audits passed on the happy
path, which means the inputs were coherent enough for the
specialists to produce sensible output. If assembly had been
broken, the audits would have caught it.

Worth flagging: this is one of those "trust the streamed output"
situations. We can verify the *result* of assembly indirectly
(audit verdicts) but not the *content*. If something seems off,
that's where extra logging or tracing would help.

### The cap-fallback is part of the design, not a workaround

When a retry cap hits, the orchestrator doesn't fail or give up
— it proceeds to the next phase with the best output it has.
The prompt makes this explicit:

> *"If the second cross_check also fails, proceed to Phase 2
> anyway with the best synthesis available."*

This is intentional. A briefing system that refuses to ship when
its auditor disagrees twice is more brittle than one that ships
with notes. Phase 1 had this same behaviour (the FinalBrief
shipped even when sense_check failed twice, because the
alternative was no brief at all).

In Phase 2 the model's narration confirms it understands the
intent. From the sense_check failure run:

> *"I've now run two sense_check cycles (initial draft failed,
> revision failed), which is the maximum allowed. Per the rules,
> I must accept the current draft and proceed to final output."*

"Accept the current draft" is exactly the right framing. Not "the
brief is broken" — "we ship the best we have, with the audit
having flagged concerns."

### The orchestrator dropped "SECTION" from final headers

A small drift to flag: the orchestrator's `FinalBrief.plain_text_body`
uses `PRICE / NEWS / CATALYSTS / GEOPOLITICS` as section headers
rather than `PRICE SECTION / NEWS SECTION / CATALYSTS SECTION /
GEOPOLITICS SECTION` (which is what draft and revise produce
internally).

This is the orchestrator's editorial normalisation. Probably fine
for an end-user brief, where "SECTION" is more useful as an
internal-pipeline marker than as a header. But it's an inconsistency
between the internal output and the final output.

The orchestrator prompt currently says *"the FinalBrief renders
the approved brief"* — which could be read either way. Could tighten
with explicit *"preserve the exact section headers from the
approved draft"* if we wanted strict pass-through. For now, the
result reads well and we're leaving it alone.

### Streaming is the right default for dev runs

The orchestrator runs with default Strands streaming (no
`callback_handler=None`). This means stdout shows:

- The orchestrator's narration between tool calls ("I'll fetch
  the price data...", "Now I'll synthesise...")
- Each tool call announced with `Tool #N: name`
- The orchestrator's reasoning at retry-cap moments

For dev runs, this is exactly what we want — we can see the
workflow execute, count tool calls, read the model's reasoning
about caps and failures. The narration is also the smoke tests'
primary source of truth (the structured `result.message` walk
is best-effort).

For deployed runs, we'd probably want this silent. The
orchestrator factory has a comment flagging this — we'll switch
to `callback_handler=None` when we move toward AgentCore
deployment.

### The smoke-test fallback to manual counting is fine

I tried to count cross_check / sense_check invocations
programmatically from `result.message.content`, but I'm not
certain the Strands AgentResult shape gives me what I need
across SDK versions. So I wrapped the structured walk in
defensive exception handling and fell back to "count manually
from the streamed Tool #N lines."

In practice, manual counting is easy — the streamed output is
clear, and the `Tool #N: cross_check` lines are visually obvious.
The structured count would be nicer but isn't necessary.

A more robust approach would be Strands' `BeforeToolCallEvent`
hooks — those could increment a counter on every tool invocation
deterministically. If we ever want pytest-grade assertion on
invocation counts, that's the path. For now, streamed-output
counting is sufficient.

## What surprised me

- **The orchestrator recognised the stub as a test scenario.** In
  the sense_check failure run, the orchestrator read the stub's
  response (which contains the phrase *"Test stub: this auditor
  always returns FAIL to exercise the orchestrator's retry-cap
  logic"*), inferred the test was about cap enforcement
  specifically, and named that in its narration before proceeding
  correctly. I expected the model to follow the rule mechanically;
  it understood *why* the rule existed. That's a richer behaviour
  than just rule-following.

- **revise applied generic stub notes successfully.** The
  sense_check stub's REVISION NOTES were deliberately vague
  ("Tighten the news section's opening to lead more directly with
  the synthesis's identified dominant narrative...") because the
  stub doesn't see the draft. revise produced a real change
  against this guidance anyway. So revise can act on general
  feedback as well as on specific quoted-text feedback. Useful to
  know for cases where audit feedback isn't perfectly precise.

- **How small the orchestrator's Python is.** The orchestrator
  agent factory is 50 lines: imports plus a single function that
  builds eight specialists and the fetch_price tool and wires
  them. Almost all the orchestration logic lives in the markdown
  prompt. This is the inverse of Phase 1, where graph.py and the
  router functions were the substance and prompts were
  per-node-specific tuning.

- **The narration at retry-cap moments is striking.** The
  orchestrator doesn't just stop — it reasons aloud about why
  it's stopping. "Per the rules, I must accept the current draft
  and proceed to final output." That's the model treating its
  prompt as a contract it's accountable to, not a script it's
  executing. Worth noting as a property of declarative prompts
  that imperative ones might not produce.

## What's NOT decided yet

Three items, all minor and post-Phase-2:

- **Streaming for production runs.** The orchestrator is verbose
  in dev. For AgentCore deployment we'd want it quieter.
  `callback_handler=None` on the orchestrator agent factory is
  the switch. Defer until deployment.
- **The SECTION-header normalisation in FinalBrief.** Leaving as-is
  for now; the result reads well. If we ever need strict
  pass-through, the prompt tightening is a small change.
- **Programmatic invocation counting.** The smoke tests fall back
  to manual counting from streamed output. If we want pytest
  assertions on invocation counts, Strands hooks
  (`BeforeToolCallEvent`) are the path. Deferred unless needed.

## Open questions

- **Cost shape over a week of natural runs.** ~10-15 cents per
  happy-path run, ~20-30 cents per failure-path run. Tractable
  for development. If the agent runs daily in production with
  typical happy-path frequency, we're at $3-5/month — fine. If
  audits start failing more often (unlikely but possible),
  costs could climb.

- **Whether the orchestrator's behaviour stays stable across
  varied market conditions.** All smoke runs so far have hit the
  same news context (Iran-Hormuz crisis, OPEC fragmentation, etc.).
  A quieter day or a completely different macro context might
  exercise the agent differently. Not testable today; worth
  watching once we deploy.

- **What happens on edge inputs.** What if `fetch_price` returns
  an error? What if `research_news` returns nothing? What if
  Tavily's API is rate-limited? The smoke tests have only
  exercised normal conditions. Failure-mode testing at the tool
  level is future work.

## Glossary

- **Declarative orchestrator prompt** — Workflow specified as goal
  + available tools + rules + constraints, rather than as a
  step-by-step recipe. The model plans the steps; the prompt
  defines the bounds. Phase 2's chosen approach.
- **Retry cap** — Hard constraint on how many cycles of an audit
  loop can run. Phase 2 caps both at 2 cycles. Enforced by prompt
  instruction alone; validated under failure conditions in PR 5.
- **Cap-fallback** — Specified behaviour when a retry cap is hit:
  proceed to the next phase with the best output available.
  Prevents the orchestrator getting stuck on persistent audit
  failures. Phase 1 had the same pattern.
- **Selective re-research** — When cross_check fails, re-run only
  the research streams listed in its `RE-RESEARCH TARGETS`,
  preserving the others. Validated in PR 5: cross_check stub
  flagged `news` only, orchestrator re-ran `research_news` only.
- **Structured-output boundary** — The point in the agent where
  text becomes typed data. In Phase 2's design, this is only at
  the orchestrator's `FinalBrief` output. Every internal handoff
  is text.
- **Stub specialist** — A drop-in replacement for a real specialist
  whose response is hardcoded. Used in failure-path smoke tests
  to deterministically trigger conditions (always-FAIL audits)
  that don't occur naturally.
