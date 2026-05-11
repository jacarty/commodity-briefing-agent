# Phase 2 retrospective — Strands Agents on Bedrock

The second implementation of the daily commodity briefing agent.
Same agent design from Phase 1 (research → synthesise → audit →
draft → audit → deliver), translated onto Strands' agents-as-tools
pattern with Claude served via Amazon Bedrock.

This retrospective is structured as a **comparison**. The project's
purpose isn't to ship one agent; it's to build the same conceptual
agent on three architectures and learn what's portable about agent
design versus what's framework-specific. Phase 2's value lies in
what it reveals when set against Phase 1.

Where Phase 1's retrospective named *what we built*, this one names
*what's the same*, *what's different*, and *what each approach
buys you*.

## At a glance

|  | Phase 1 (LangGraph) | Phase 2 (Strands / Bedrock) |
|---|---|---|
| **Pattern** | Declarative state graph | Agents-as-tools (model-driven) |
| **Components** | 12 nodes + 2 routers | 1 orchestrator + 8 specialists + 1 plain tool |
| **Workflow lives in** | Code (graph.py edges) | Prose (orchestrator system prompt) |
| **Inter-node data** | Typed (TypedDict + Pydantic schemas) | Text (section-header conventions + VERDICT lines) |
| **Routing** | Conditional edges + Literal enums | Model interpretation of `VERDICT: PASS/FAIL` |
| **State carrier** | Shared `State` TypedDict | Orchestrator's conversation history |
| **Retry counters** | Integer fields in state | Counted from tool-call history in prose |
| **Final output** | `with_structured_output(FinalBrief)` | `structured_output_model=FinalBrief` |
| **Search backend** | Anthropic `web_search_20250305` server-side | Tavily via `strands-agents-tools` |
| **Model** | Claude Sonnet 4.5 (direct API) | Claude Haiku 4.5 via Bedrock (eu.) |
| **Build duration** | 13 tutorial steps, multi-week | 7 tutorial steps, days |
| **Cost per happy run** | Single-digit cents | ~10–15 cents |
| **Validation** | ~35 pytest tests against real APIs | Manual smoke tests (8 runners) |
| **Lines of Python** | Larger (state plumbing + node fns) | Smaller (specialist factories + 1 orchestrator) |
| **Prompt complexity** | Per-node prompts, mostly small | Per-specialist prompts + 1 large orchestrator prompt |

The differences are substantive. The agent's *editorial behaviour*
(what makes the brief good — tone, hedging discipline, embedding
metrics in prose, pass-bias audits) is nearly identical because
that lives in prompts that ported verbatim. Everything *around*
those prompts — how data flows, how routing works, how state is
carried — is different.

## Architecture: state graph versus model-driven orchestration

### What Phase 1 did

`StateGraph` with 12 nodes connected by explicit edges, plus two
conditional edges that routed on integer retry counters in state.
Reading `graph.py` gave you the workflow: each node was a small
function that read from state, called an LLM with
`with_structured_output`, and wrote back. State was the carrier —
nodes never spoke to each other directly.

Phase 1 retrospective named this as "state-first design": you
defined the state schema before writing nodes, because state
absorbed inter-node communication. The result was small nodes
(most under 30 lines) and unambiguous topology.

### What Phase 2 did

One orchestrator agent with eight specialists wired into its
`tools=[]` list. The workflow lives in the orchestrator's system
prompt: "first call fetch_price, then research, then synthesise,
then audit with cross_check, then..." The model interprets the
prompt at runtime and calls specialists in order.

There is no shared state. Specialists are stateless across calls
— their context resets between invocations. The orchestrator's
conversation history is the only carrier of information across
specialist calls, and the orchestrator must package upstream
outputs into a single input string when calling each downstream
specialist.

### Which is better

Neither, but they buy different things.

**Phase 1 gives you static visibility.** Read `graph.py` and you
know exactly what happens, in what order, under what conditions.
You can diff the topology in a code review. You can prove
properties (e.g., "the brief always passes through sense_check")
by reading the edges.

**Phase 2 gives you smaller surface area.** The orchestrator's
Python is 50 lines; everything else is prompts. Adding another
specialist is a 12-line factory function and a markdown file.
Changing workflow logic is a markdown edit, not a code change.

**Phase 1 gives you deterministic routing.** Conditional edges
match against Literal enums; routing is exact.

**Phase 2 gives you semantic routing.** The orchestrator reads
`VERDICT: PASS` versus `VERDICT: FAIL` as the first line of a
prose response, and routes from there. Validated in PR 3/4/5 to
work reliably; not as deterministic as enum matching but
sufficient.

**Phase 1 makes retry caps trivial** (a counter incremented in
state). **Phase 2 makes retry caps a prompt constraint.** STEP-03
named the latter as the riskiest design decision in Phase 2;
PR 5 closed it positive. The model counts tool-call cycles from
its own conversation history and stops at the named limit. It
also reasons about *why* it's stopping in narration:

> *"I've now reached my retry cap for cross_check (2 cycles
> maximum). The second cross_check has failed, so per workflow
> rules, I must proceed to Phase 2 with the best synthesis
> available."*

That kind of self-explanation is something the imperative graph
in Phase 1 didn't produce.

## Data flow: typed contracts versus text-with-conventions

### Phase 1's approach

Every node-to-node hop was Pydantic-typed.
`NewsResearch(items=[NewsItem(...)])` flowed from research_news
into synthesise. `Synthesis(dominant_narrative=...,
cross_stream_signals=...)` flowed into cross_check. The
`with_structured_output` API on every LLM call enforced these
contracts at provider level — no parsing problems, no malformed
data ever reaching a downstream node.

### Phase 2's approach

Research specialists return prose with section markers (`ITEM 1`,
`EVENT 1`, `THEME 1`). Synthesise returns prose with the five
section headers. Auditors return prose starting with
`VERDICT: PASS` or `VERDICT: FAIL`. Only the final boundary
(`FinalBrief` produced by the orchestrator) is typed.

STEP-03 called this the **text-native bet** and named hybrid
promotion (`structured_output_model` per specialist) as the
fallback. The hybrid fallback was never used. Across all five
PRs, no specialist's text-native output produced an issue that
typed contracts would have prevented.

### What text-native cost

Three concrete frictions:

1. **Preamble drift.** Tool-equipped specialists (the three
   research agents) consistently added a preamble — "Based on my
   research..." — before the first structural marker. 7 out of 7
   runs across three specialists. Mild and parser-tolerable, but
   it's a structural property of how Bedrock-Claude responds to
   tool-using prompts.
2. **EVENT-block duplication** (one occurrence). A catalysts run
   produced the same EVENT block twice — once inline, once in a
   code fence. Has parse-correctness implications. Hasn't recurred,
   but the design risk is real.
3. **Section heading normalisation in FinalBrief.** The orchestrator
   dropped "SECTION" from the section headers when assembling the
   final output (`PRICE / NEWS / CATALYSTS / GEOPOLITICS` rather
   than `PRICE SECTION / NEWS SECTION / ...`). Probably fine for
   end users but it's an editorial drift Phase 1's enum-typed
   sections couldn't have produced.

None of these are blockers. All would be eliminated by typed
contracts. The text-native bet was net positive because the cost
was low and the simplification was real.

### A pattern in the drift

Preamble drift correlated perfectly with whether the specialist
had bound tools:

- Tool-equipped specialists (research × 3): preamble 7/7
- Tools-less specialists (synthesise, cross_check, draft,
  sense_check, revise): preamble 0/10

Hypothesis: the search-reason-respond loop that tool-equipped
specialists run internally leaks "let me summarise what I found"
narration into the final response. Tools-less specialists go
directly from input to structured prose with no intermediate
state to leak.

This is a real architectural property, not a per-prompt quirk.
The orchestrator's eventual parser logic simplifies because of
it: only four specialists (the research three plus a hypothetical
fourth) need preamble-tolerant parsing; the other six can be
read strictly from the first character.

## What ported verbatim

The biggest single finding of Phase 2: the editorial substance
of every prompt ported from Phase 1 unchanged. Specifically:

- **Pass-bias auditor framing** — "Bias toward passing," "A few
  minor issues is okay," "Would a competent reader notice this
  problem?" Both auditors validated against the same
  fabrication-injection pattern in PR 3 and PR 4 and produced the
  right calibration. Pass with optional notes when the issue is
  minor; fail with specific quotes and actionable revision notes
  when material.
- **Anti-weasel synthesise** — the `RISKS TO VIEW` section is the
  place to hedge; other sections commit. Concrete structural
  framing beats abstract "avoid weasel words." Held across all
  smoke runs.
- **Embed metrics in prose, never bullet-list them** in draft.
  Held. Multiple runs produced briefs with specific numbers
  ($97.66, 7 mbpd, 20%) embedded in flowing prose.
- **"Targeted revision, not a rewrite"** in revise. Bolded in the
  prompt as the single emphatic instruction. Validated in PR 4
  with side-by-side similarity ratios: revise produced 100% / 100%
  / 93% / 100% across the four sections — exactly the surgical
  behaviour wanted.
- **Inverted pyramid** — most important content first in each
  section. Held.
- **"Use confidence honestly"** in geopolitics — model uses "low"
  ratings when warranted, including in smoke runs.

These all transferred because they're about how Claude reasons
under instruction, not about LangGraph state plumbing. The
mechanical changes per prompt — strip template variables, add
output-format sections — were small and identical across all 10
prompts.

This is the most reusable lesson of Phase 2: **prompt-level
discipline is portable; framework-level scaffolding is not**.
Phase 3 (Vertex / Gemini) will tell us whether this generalises
to a different model family, but for Bedrock-Claude, the answer
is clear.

## What changed mechanically

Most prompt template variables ported unchanged in *editorial
content* but had to be **structurally removed**. Phase 1 prompts
had `{commodity}`, `{target_date}`, `{briefing_spec}`,
`{research_plan}`, `{feedback}`, `{instructions}`, plus stream-
specific variables like `{news_research}`, `{synthesis}`. All of
these worked because LangGraph's state assembled them at
template-render time.

In Phase 2, these variables disappeared. Runtime context (date,
commodity, feedback, prior outputs) is passed via the input
string when the orchestrator calls the specialist. Specialists'
system prompts became *standing instructions* — what kind of
research the specialist does, what output format it produces,
what to skip — rather than per-invocation templates.

This is the **mechanical** part of the port. The **editorial**
substance survives.

## Validation: pytest harnesses versus manual smoke tests

### Phase 1's approach

~35 pytest tests against real APIs (Anthropic, yfinance). The
tests covered nodes individually plus end-to-end. Each test had
a deterministic fixture (e.g., a known briefing spec on a known
date) and assertions about the output shape. Tests were
expensive per run (~$0.10–0.30 in API calls plus ~3 minutes of
wall time) but the harness paid for itself by catching
regressions during prompt iteration.

### Phase 2's approach

Eight manual smoke test runners, no pytest, no programmatic
assertions:

| Runner | Purpose | Cost per run |
|---|---|---|
| `smoke_fetch_price` | Plain tool sanity | free (yfinance only) |
| `smoke_research_news` | One research specialist | ~$0.01 |
| `smoke_research_catalysts` | One research specialist | ~$0.01 |
| `smoke_research_geo` | One research specialist | ~$0.01 |
| `smoke_synthesise` | Live chain: research × 4 → synthesise | ~$0.05 |
| `smoke_cross_check` | Live chain + dual scenario | ~$0.06 |
| `smoke_draft` | Live chain + draft | ~$0.05 |
| `smoke_sense_check` | Live chain + dual scenario | ~$0.06 |
| `smoke_revise` | Live chain + chained revise with diff | ~$0.06 |
| `smoke_orchestrator` | Full happy path | ~$0.13 |
| `smoke_orchestrator_failure` | cross_check stub + retry cap | ~$0.25 |
| `smoke_orchestrator_failure_sense` | sense_check stub + retry cap | ~$0.20 |

Manual inspection of stdout, no assertions, no test harness.

### Which was right

For Phase 1: the pytest harness was correct. LangGraph nodes are
testable in isolation; assertions about typed outputs are
straightforward; regressions during prompt iteration are frequent
and worth catching.

For Phase 2 *as a learning project*: manual smoke tests were
correct. They're cheaper to write, faster to run individually,
and they expose the model's narration which is itself useful
data (e.g., the orchestrator's cap-recognition narration). pytest
would have added overhead without proportional value for a
build-and-validate-once project.

For Phase 2 *if it were productionised*: pytest would matter more.
Specifically: invocation-count assertions on the retry-cap tests
(via `BeforeToolCallEvent` hooks) would replace manual counting
from streamed `Tool #N` lines. Worth doing if the orchestrator
ever runs against real production traffic.

The decision was correct for the project's purpose. Worth being
honest that "manual smoke tests only" is not a scalable
validation strategy.

## What the agents-as-tools pattern bought us

Three concrete benefits over Phase 1:

1. **Self-narrating workflow.** The orchestrator narrates each
   step ("Now I'll synthesise...", "Cross_check passed; moving
   to draft..."). For dev debugging this is gold — you see the
   workflow execute and the reasoning at decision points. Phase
   1's graph had no equivalent; you knew the topology from code
   but execution was silent unless you wired logging.
2. **Specialist isolation.** Each specialist is a separate Agent
   with its own prompt, model, and (sometimes) tools. Swapping a
   specialist is one factory function change. The stub-specialist
   pattern for failure-path testing only works because of this
   isolation — Phase 1 would have needed monkey-patching to do
   the same kind of test.
3. **Workflow as markdown.** The orchestrator's workflow lives in
   a markdown file. Changes to retry caps, fallback behaviour, or
   audit gating are markdown edits, not code edits. The change
   shows up as a prompt diff in PR review, which is more
   reviewable than a graph-topology change in some ways and less
   in others.

## What the agents-as-tools pattern cost us

Two concrete frictions:

1. **No static visibility.** You can read the orchestrator prompt,
   but you can't *prove* that the orchestrator will follow it.
   Validation has to be empirical — run it, watch what happens,
   trust the narration. In Phase 1, the graph topology *is* the
   proof.
2. **Input-string assembly is hidden.** The orchestrator packages
   upstream outputs into a single string for the next specialist,
   but we never see exactly what string. We can verify it
   indirectly (audits pass), but the actual content is between
   the orchestrator and the specialist. If something goes wrong
   in assembly, we'd need extra logging or tracing to debug it.

## Cost shape

| Phase | Cost per typical run |
|---|---|
| Phase 1 (Anthropic direct, full chain + tests) | ~$0.30–0.50 |
| Phase 2 (Bedrock Haiku 4.5, full chain) | ~$0.13 happy-path |
| Phase 2 (Bedrock Haiku 4.5, with retry) | ~$0.20–0.25 |

Phase 2 is significantly cheaper per run, driven by Haiku 4.5
versus Phase 1's Sonnet 4.5 plus Anthropic web_search costs (the
latter was a real chunk of Phase 1's bill).

Validation cost was also different: Phase 1's ~35 pytest tests
cost ~$5–10 per full run; Phase 2's smoke tests are individual
runs of ~$0.05–0.25 each, no test-suite cost.

## Where lessons should NOT be transferred

A few Phase 1 lessons that don't apply to Phase 2:

- **"`with_structured_output` is the workhorse, agent loops the
  exception."** Phase 1's retrospective named this as the biggest
  pattern lesson. It's wrong for Phase 2. The whole point of
  Strands is that the orchestrator *is* an agent loop; we use the
  agent pattern eight times (once for each specialist) plus the
  orchestrator. `structured_output_model` is used exactly once,
  at the boundary.
- **State-first design.** No state to design in Phase 2. The
  equivalent is **prompt-first design** — write the specialist's
  prompt, design its output structure, define what the
  orchestrator will pass it.
- **Schemas-as-contracts at every node-to-node hop.** Phase 2
  uses contracts only at the boundary. Internal hops are text.

What *does* port:

- **Bounded loops with explicit caps.** Phase 2 has them as prose
  constraints; Phase 1 had them as state counters. Same shape,
  different mechanism. Both work.
- **Pass-bias prompts for auditors.** Same instructions, same
  result.
- **Two-stage analyse-then-render.** Same structural pattern.
- **Editorial discipline.** All of it.

## Open questions going into Phase 3

A few things Phase 2 didn't answer, that Phase 3 will:

- **Does prompt-level discipline port to a different model family?**
  Pass-bias, anti-weasel, embed-don't-bullet — these all work for
  Claude. Whether they work for Gemini at similar quality is the
  open question. If they do, we have strong evidence that
  prompt-level patterns generalise. If they don't, we have
  evidence that they're family-specific.
- **Does the agents-as-tools pattern translate to Vertex Agent
  Engine?** Phase 3 uses a different orchestration framework
  again. Whether the same component decomposition (1 orchestrator
  + 8 specialists + 1 plain tool) holds in Vertex is a real test.
- **What's the right cost-quality tradeoff across model
  families?** Phase 1 used Sonnet; Phase 2 used Haiku and got
  excellent results at lower cost. Phase 3 will give us Gemini
  pricing and quality data.

## The biggest lesson

**Prompt-level discipline is the portable layer.** Architecture
choices, framework conventions, validation strategies, and cost
shapes all changed substantially between Phase 1 and Phase 2.
What didn't change was *what the briefs say and how they say it*.
That lives in prompts that ported verbatim — pass-bias auditing,
inverted pyramid, embedded metrics, hedging discipline, source
grounding.

If Phase 3 produces the same finding (different framework, same
editorial quality from the same prompts), then we have a real
result about agent design: **the framework is the scaffolding,
the prompts are the substance**. Pick whichever framework matches
your operational requirements; carry the prompts forward.

That's the hypothesis Phase 3 will test.
