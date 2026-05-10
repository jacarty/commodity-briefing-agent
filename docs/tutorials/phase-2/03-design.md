# STEP-03 — Design

The agents-as-tools translation. This step is the design discussion
that bridges "we know what we're building" and "we're ready to write
code." It's the equivalent of Phase 1's STEP-03, but the work is
different — Phase 1's STEP-03 designed an agent from scratch; this
one translates an existing design onto different primitives.

A note on epistemic status: this is a starting design, written
*before* implementation. Several decisions will be revisited as we
build. That's expected. The goal is a design that's coherent,
internally consistent, and surfaces the open questions — not a
final design.

## What we're designing

The same agent as Phase 1, on Strands' agents-as-tools pattern.
Component count drops from Phase 1's 14 things (12 nodes + 2
routers) to 10 — collapsing happens because Strands' model-driven
orchestration absorbs the work that Phase 1 encoded as graph
topology.

Final component list:

| Component | Type | Returns |
|---|---|---|
| Orchestrator | top-level Agent | `FinalBrief` (Pydantic, structured) |
| `research_news` | specialist agent | text |
| `research_catalysts` | specialist agent | text |
| `research_geo` | specialist agent | text |
| `synthesise` | specialist agent | text with section headers |
| `cross_check` | specialist agent | text starting with `VERDICT: PASS/FAIL` |
| `draft` | specialist agent | text with section headers |
| `sense_check` | specialist agent | text starting with `VERDICT: PASS/FAIL` |
| `revise` | specialist agent | text with section headers |
| `fetch_price` | plain tool | structured price data (no LLM) |

What disappears from Phase 1: `plan` (orchestrator's reasoning is
the plan), `re_research` (orchestrator just calls a research
specialist again with feedback), the two router functions and their
retry counters (orchestrator's prompt encodes the retry caps),
`deliver` (becomes the orchestrator's structured final output).

## What we learned

### Strands offers three ways to wire agents-as-tools

The docs surface three:

- **Pass agents directly** in `tools=[research_agent, ...]`. SDK
  auto-converts each to a tool with `input: str` → text response.
- **`.as_tool(name=, description=)`** — same, but customises tool
  metadata and lets you preserve context across calls.
- **`@tool`-decorated wrapper functions** — write a custom function
  that internally creates an Agent. More boilerplate, more control,
  needed if you want to return Pydantic objects from a specialist.

We're going with the first option (pass agents directly). Specialists
return text by default — this is the **text-native** stance.

### Text-native is the bet

Phase 1 used typed contracts at every node-to-node hop —
`NewsResearch`, `Synthesis`, `CrossCheckResult`, `Brief` — all
Pydantic. The orchestrator-as-LLM model breaks this. Specialists
return strings; the orchestrator reads them and reasons.

The bet: the model can reliably carry structure through prose. The
section-heading convention (`DOMINANT NARRATIVE\n\n[paragraph]\n\n
PRICE INTERPRETATION\n\n[paragraph]\n\n...`) imposes enough
structure that downstream specialists can locate what they need by
reading. The auditors' `VERDICT: PASS/FAIL` opening line gives the
orchestrator a near-deterministic routing signal without breaking
the text-native pattern.

If text-native fails — auditors interpreted ambiguously, synthesis
sections skipped, orchestrator misreading content — the fallback is
**hybrid**: introduce `structured_output_model` on the specialists
that need it, while keeping the rest text-native. The most likely
first hybrid candidate is `synthesise` (if `cross_stream_signals`
sections are skipped) or the auditors (if `VERDICT:` interpretation
proves unreliable).

The principle: text-native first, hybrid where quality forces it.

### The orchestrator becomes the workflow specification

In Phase 1, the workflow lived in graph topology — read `graph.py`
and you could see the order of operations, the parallel research
fan-out, the conditional routing. In Phase 2, the workflow lives
*in the orchestrator's prompt*, expressed as instructions for when
to call which specialist.

This is a major shift. Phase 1's `graph.py` was code — readable,
diffable, version-controlled, the unambiguous source of truth for
the topology. Phase 2's orchestrator prompt is markdown — readable,
diffable, version-controlled, but interpreted by an LLM at runtime,
which means its enforcement is probabilistic rather than guaranteed.

The orchestrator's prompt will need to encode:

1. The workflow sequence (fetch price; call research specialists in
   parallel; assemble outputs; call synthesise; call cross_check;
   route based on VERDICT; call draft; call sense_check; route
   based on VERDICT; produce final structured output).
2. The retry caps (no more than two re-research cycles, no more
   than two revise cycles).
3. The input-assembly rules (concatenate prior specialist outputs
   into a single string when calling the next specialist).
4. The fallback behaviour when caps are hit (proceed with what we
   have).

This is a long prompt. Probably the longest in the project. We'll
draft it when we touch code.

### Specialists are stateless by default

Strands' default: agents passed as tools reset their conversation
context between invocations. Each call starts fresh. You opt in to
context preservation with `preserve_context=True`.

For our specialists, default-stateless is correct. The research
specialists shouldn't accumulate context across calls — each
invocation should be a focused research task with the inputs it
needs passed in explicitly. Same for the auditors and the renderers.

What replaces shared state: **the orchestrator's conversation
history.** When the orchestrator calls `research_news`, the
specialist's response goes into the orchestrator's context. When
the orchestrator later calls `synthesise`, it constructs a single
input string from those prior responses and passes it explicitly.
The orchestrator is the carrier of context, not a shared state
object.

This means:

- Specialist signatures matter — each specialist takes whatever it
  needs as the input string, no implicit state reads.
- The orchestrator does the input-assembly work that LangGraph's
  `State` TypedDict did automatically in Phase 1.
- Context flows are explicit and traceable in the orchestrator's
  reasoning — but the orchestrator has to remember to do the
  assembly correctly.

### Tavily lives on each research specialist, not on the orchestrator

The research specialists each have Tavily bound directly:

```python
research_news = Agent(
    name="research_news",
    description="Research recent oil-related news...",
    system_prompt=load_prompt("news"),
    model=BEDROCK_HAIKU,
    tools=[tavily_search],
)
```

The orchestrator never sees Tavily. The reason: each research
specialist has domain-specific judgement about what to search for
and how to evaluate results. If Tavily is on the orchestrator, the
orchestrator has to decide *how* to search for news vs catalysts vs
geopolitics, which dilutes its role and forces it into specialist
territory.

This is a small choice but worth flagging because it's the kind of
thing that can drift later — putting tools on the orchestrator for
"convenience" tends to expand the orchestrator's responsibilities
past orchestration.

### Two auditors stays, retry caps in prose

Phase 1's two-stage analyse-then-render pattern preserved:
cross_check audits synthesis-vs-research; sense_check audits
draft-vs-synthesis. Each catches a different failure mode at a
different layer.

In Phase 2 these become two retry loops in the orchestrator's
prompt. The orchestrator is responsible for tracking how many times
each loop has fired and stopping at two. Phase 1 had this as
counters in state checked by router functions; Phase 2 has it as
prose instructions.

This is the most consequential test of model-driven orchestration
in the project. Either the model reliably enforces "no more than
twice" from prompt instruction, or it doesn't. If it doesn't,
options are:

1. Tighten the prompt with stronger imperatives and concrete examples
2. Track attempts in a tool the orchestrator can call (programmatic
   safety net wrapped as a `@tool`)
3. Fall back to `Graph` for the audit loops specifically

Going with the first option until we see what happens. The "watch
during build" approach.

### Phase 1's prompt-level lessons port unchanged

Several lessons from Phase 1 are about LLM behaviour, not framework
mechanics, and will land verbatim in Phase 2:

- **Pass-bias auditors** — without explicit "what is NOT a flagged
  issue" guidance, auditors over-flag. The instruction lives in the
  cross_check and sense_check system prompts.
- **Anti-weasel synthesise** — the `dominant_narrative` is the
  place to commit; `risks_to_view` is the place to hedge. Concrete
  structural framing beats "avoid weasel words."
- **Embed metrics, never bullet-list them** in draft — dashboards
  report; briefs analyse.
- **Voice instructions need to be concrete** — "senior analyst
  briefing colleagues" beats "professional."
- **Don't rewrite the prose** in the rendering specialists —
  revise's job is targeted fixes, not fresh drafts.
- **Inverted pyramid in draft** — most important content first.

These all carry over because they're about how Claude responds to
instruction shape, not about LangGraph or Strands.

### Two-stage analyse-then-render survives

The architectural pattern Phase 1's retrospective named as most
likely portable — separate analytical work (synthesise) from
rendering (draft), audit each layer at its own level — works
cleanly in agents-as-tools. Synthesise is a specialist; cross_check
is a specialist; draft is a specialist; sense_check is a specialist.
The orchestrator runs them in the same logical order Phase 1's
graph did.

This is the first meaningful evidence that the design isn't
entirely LangGraph-shaped. Whether the rest of Phase 1's lessons
transfer as cleanly is what the build will tell us.

### deliver becomes the orchestrator's final output, not a specialist

The Phase 1 `deliver` node produced `FinalBrief` (subject,
html_body, plain_text_body) — the email-shaped output a downstream
service consumes. In Phase 2, instead of being a separate
specialist, this becomes the orchestrator's own structured output
via `structured_output_model=FinalBrief`.

Reason: deliver was barely a specialist in Phase 1 anyway — its
prompt said "render the brief as written, don't edit." It's mostly
a format conversion. Putting that conversion in the orchestrator's
final-output schema is the cleanest text-native approach: every
internal step is text; only the boundary is structured.

This is the one place the `structured_output_model` mechanism is
used in the design as drafted. Hybrid promotions during build will
add more.

## What we'll be watching for

Specific things the build needs to validate:

- **Does the orchestrator reliably enforce two retry loops from
  prose alone?** The hardest test of model-driven orchestration in
  the design. If it fails, programmatic safety nets are the first
  fallback.
- **Does text-native synthesise reliably produce the
  cross_stream_signals section?** Phase 1's schema *required* the
  field; the model had to fill it. In text-native, it's a section
  header in prose — the model can skip it. Cross_stream_signals
  was the most analytically valuable field in Phase 1's synthesis;
  if it goes missing, briefs will lose their cross-stream insight.
- **Is the `VERDICT: PASS/FAIL` opening line interpreted correctly
  by the orchestrator?** This is the structural mitigation for
  audit-decision ambiguity. If the orchestrator routinely misreads
  it (passing failed audits, failing passed ones), the auditors
  are the natural first hybrid candidate.
- **Does the orchestrator manage input-string assembly reliably?**
  Concatenating prior specialist outputs into a single string for
  the next specialist is workflow logic the orchestrator's prompt
  has to encode. If the orchestrator forgets to include something,
  downstream specialists work from incomplete inputs and the failure
  may not surface as an audit failure.
- **Does revise stay distinct from draft in practice?** Phase 1's
  revise was mostly idle code (sense_check usually passed). If
  Phase 2's revise rarely fires, that's expected. If revise fires
  but produces fresh drafts instead of targeted fixes, the prompt
  isn't holding the distinction and we may need to collapse the
  two.

## What's not decided

A few things deferred to later steps:

- **The orchestrator's full system prompt.** Sketched here in
  intent, written for real when we have at least one specialist
  working and can test orchestration end-to-end.
- **Specialist system prompts.** Phase 1's prompts get copied into
  Phase 2's `prompts/` directory verbatim, then adjusted only if
  Bedrock-Claude needs different wording (which we won't know
  until we run them).
- **Implementation order.** Which specialist do we build first?
  STEP-04 picks that up.
- **Tool descriptions.** Each specialist needs a `description=`
  field on its Agent that the orchestrator reads to decide when to
  call. Drafted alongside the system prompts.
- **Streaming control for specialists.** Phase 2's hello-world
  surfaced that Strands streams to stdout by default. We'll need
  to control this for non-interactive specialist calls — TBD how
  cleanly Strands lets us silence it.

## What's settled

For reference, decisions made through this step:

- **Pattern**: agents-as-tools, pass agents directly in `tools=[]`
- **Default return type**: text from specialists; structured (Pydantic)
  only at the orchestrator's final output boundary
- **Hybrid criterion**: text-native first, hybrid where quality
  forces it; the most likely first hybrid candidates are synthesise
  (if cross_stream_signals goes missing) and the auditors (if
  VERDICT interpretation is unreliable)
- **Section-heading convention** for prose with internal structure
  (uppercase headers, blank lines as separators)
- **`VERDICT: PASS/FAIL`** as the opening line for both auditors
- **Tavily binding**: per-specialist, not on the orchestrator
- **Two auditors**: cross_check + sense_check, both with retry caps
  in the orchestrator's prompt
- **Retry caps**: prose instructions to start; programmatic safety
  net only if the prose proves unreliable
- **Two-stage analyse-then-render**: preserved
- **`plan` and `re_research`**: collapsed into the orchestrator
- **`deliver`**: collapsed into the orchestrator's structured final
  output
- **Phase 1 prompt-level lessons**: port verbatim (pass-bias,
  anti-weasel, embed-don't-bullet, don't-rewrite, inverted pyramid)

## Glossary

- **Agents-as-tools** — Strands pattern where one orchestrator agent
  treats specialist agents as callable tools. Hierarchical
  delegation. The orchestrator's prompt encodes the workflow.
- **Text-native** — Design stance where specialists return prose by
  default. Structure is imposed via prose conventions (section
  headers, VERDICT lines) rather than typed return values. Contrasts
  with Phase 1's typed-everywhere approach.
- **Hybrid** — Selective use of `structured_output_model` on
  specialists where text-native proves insufficient. The fallback
  position for text-native; not the starting design.
- **Workflow-as-prompt** — The pattern where the agent's workflow
  is encoded in the orchestrator's prompt rather than in code
  topology. The defining shift from Phase 1.
- **Section-heading convention** — Prose structure where named
  sections are introduced by uppercase headers (e.g. `DOMINANT
  NARRATIVE`) and separated by blank lines. The text-native
  alternative to Pydantic field names.
- **VERDICT line** — Required opening line of an auditor's response
  (`VERDICT: PASS` or `VERDICT: FAIL`). The minimum structure
  imposed on auditor prose to make orchestrator routing decisions
  near-deterministic.
- **Stateless specialist** — A specialist whose context resets
  between invocations. Strands' default. Inputs flow through the
  orchestrator's input string; outputs flow back as the
  specialist's response.
