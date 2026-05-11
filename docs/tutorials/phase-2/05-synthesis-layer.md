# STEP-05 — The synthesis layer

The synthesis layer is live. `synthesise` reads the four research
outputs plus price data and produces structured interpretation;
`cross_check` audits that synthesis against the underlying research
and emits a `VERDICT: PASS / FAIL` line that gates progress to
drafting.

This step covers PR 3 — both specialists built and smoke-tested.

## What I did

- Built `synthesise` as the first non-research specialist. No
  bound tools (reasons over inputs rather than searching), same
  factory pattern as the research specialists, five mandatory
  section headers in the output (DOMINANT NARRATIVE, PRICE
  INTERPRETATION, CROSS-STREAM SIGNALS, RISKS TO VIEW, HEADLINE
  METRICS).
- Wrote a live-chain smoke test for synthesise — runs all four
  research sources sequentially, concatenates their outputs plus
  the price dict and a briefing spec into a single input string,
  feeds it to synthesise. First end-to-end exercise of the
  input-assembly pattern STEP-03 flagged.
- Built `cross_check` as the first auditor. Same template
  (`tools=[]`, `callback_handler=None`), but with the
  `VERDICT: PASS / FAIL` opening-line convention from STEP-03 plus
  the structured output sections (SUMMARY, CONSISTENCY ISSUES,
  CALIBRATION ISSUES, GROUNDING ISSUES, RE-RESEARCH TARGETS).
- Wrote a dual-scenario smoke test for cross_check: the same live
  chain plus two cross_check invocations, one with the real
  synthesis (expected PASS) and one with the synthesis corrupted
  by an injected fabricated claim (expected FAIL).
- Logged five new observations across the two PRs in
  `docs/observations.md`.

## What I learned

### The synthesis layer maps cleanly onto agents-as-tools

Phase 1's synthesise node was a reasoner; Phase 1's cross_check
node was an auditor. STEP-03 said these would become specialists
without bound tools, with their own output conventions (section
headers for synthesise, VERDICT line for cross_check). They did.
The translation was mechanical — strip state-driven template
variables, add output-format sections to the prompt, switch the
return type from Pydantic schemas to structured prose.

The implementation work was an hour or two per specialist. Most
of the time was reading the Phase 1 prompts carefully to figure
out which parts ported verbatim (editorial substance) and which
parts needed re-shaping (template variables and field references).

### `tools=[]` is intentional, not omission

The research specialists all had `tools=[tavily_search]`.
Synthesise and cross_check don't. The empty list is meaningful —
it says "this specialist reasons over what the orchestrator gives
it, no external lookups." A future maintainer reading the
specialist factory should see the empty list as a positive
statement of design, not a missing argument.

Adding a code comment to that effect in each tools-less specialist
felt slightly defensive but cheap. Worth doing for clarity.

### The input-assembly pattern is real and worth pulling out

Synthesise needs all four research outputs plus price data plus
the briefing spec, concatenated into one input string. STEP-03
flagged this as workflow logic the orchestrator's prompt has to
encode. The smoke test had to do that assembly directly because
there's no orchestrator yet.

I pulled the assembly out into a function (`assemble_synthesise_input`)
in the smoke test, rather than letting it sprawl across the main
flow. Reasons:

- The function is reusable when we wire the orchestrator (either
  as inspiration for the orchestrator's prompt, or as a real Python
  helper if we ever go partly hybrid).
- It separates "gather research" from "package research for the
  next specialist," which are conceptually different concerns.
- It's the natural unit to test if we later want pytest coverage
  of input assembly independent of LLM calls.

The same shape repeated for cross_check's `assemble_cross_check_input`.
Two functions per smoke test feels like the right granularity.

### The VERDICT line convention works

This was one of STEP-03's named "things we'll be watching for."
The risk: cross_check returns prose, the orchestrator has to
interpret whether the audit passed, ambiguity in interpretation
costs us routing decisions.

The mitigation in STEP-03: demand a `VERDICT: PASS` or
`VERDICT: FAIL` line at the start of cross_check's response, so
the orchestrator's parser can read line 1 and route deterministically.
The rest of the output is for reasoning and downstream use.

It worked. Both cross_check runs led with exactly the required
line, both runs honoured the rest of the output structure. The
orchestrator (when it lands) will read line 1, match
`^VERDICT: (PASS|FAIL)`, and route. No fuzzy interpretation needed.

### Pass-bias prompts port verbatim from Phase 1

Phase 1's cross_check had a load-bearing prompt-engineering
lesson: auditors over-flag without explicit pass-bias instructions.
Phase 1's prompt encoded this with four bullets — *"Bias toward
passing," "Re-research is expensive," "You don't have to find
issues," "A few minor issues is okay"* — plus a "what is NOT a
cross-check issue" list, plus the framing question *"would a
competent reader of this synthesis reach a wrong conclusion?"*

All of that ported into Phase 2's cross_check.md verbatim. And the
result: the auditor passed the clean synthesis without inventing
issues, and failed the corrupted synthesis with a specific,
correct flag. Two-for-two.

The lesson: when a Phase 1 prompt has explicit guidance about
behaviour the model would otherwise drift on, that guidance is
about Claude, not LangGraph. It transfers.

### The fabrication injection is a good test design

Scenario 2 took the real synthesis from the live chain, inserted
a plausible-but-fabricated Goldman Sachs $147 oil forecast into
the HEADLINE METRICS section, and fed the corrupted synthesis
into cross_check. The auditor:

1. Returned `VERDICT: FAIL` on line 1 (correctly routing)
2. Identified the fabrication by name and content in GROUNDING
   ISSUES
3. Correctly placed `news` in RE-RESEARCH TARGETS, because the
   fabricated claim is an analyst forecast and news is where such
   claims would land

This pattern — "real upstream output, inject one specific known-bad
thing, see if the downstream specialist catches it" — is the right
shape for testing detection. It's stronger than handcrafting bad
input (the rest of the synthesis is otherwise legitimate, so the
auditor has to find the needle in a real haystack) and stronger
than only testing the pass case (which doesn't test detection at
all).

Worth using this pattern for the second auditor (sense_check) when
we land it in PR 4.

### Preamble-drift hypothesis is real

After synthesise (no preamble across two runs) and cross_check
(no preamble across two runs), the standing count is:

- Tool-equipped specialists: preamble 7/7
- Tools-less specialists: preamble 0/4

11 runs across 5 specialists. The pattern: preamble drift
correlates with bound tools, not with specialist type or output
shape.

The plausible mechanism: tool-equipped specialists run a
reason-act-observe loop internally (search → reason → maybe search
again → respond). Some of that intermediate reasoning ("here's
what I found, here's what I conclude...") leaks into the final
response as preamble. Tools-less specialists go directly from
input to structured response with no intermediate state to leak.

If this holds for draft, revise, and sense_check (all tools-less),
the orchestrator's parser can read tool-equipped output leniently
(skip lines until a structural marker) and tools-less output
strictly (the first line is the marker). The parser logic
simplifies.

The retrospective will need to revisit this if PR 4 contradicts it.

### Live-chain smoke tests are valuable but expensive

Each PR 3 smoke run cost roughly 3-6 cents — four Tavily-bound
research specialists with 1-3 searches each, plus a synthesise
call, plus (in cross_check's case) two cross_check calls. Single
digit cents is fine; running the full chain a few times during
development is sustainable.

But this scales with specialist count. A full orchestrator run
will hit 8+ specialists, some of them twice (re-research, revise
loops). End-to-end testing the orchestrator will be ~10-15 cents
per invocation. That's still tractable, but at "20 invocations a
day during development" it adds up.

Worth thinking about whether some specialists can be smoke-tested
in isolation with hardcoded inputs (draft and revise probably can
— they consume structured prose that we can pin) while the
orchestrator end-to-end is tested less frequently.

Not deciding now. Logging the cost shape as a consideration.

## What surprised me

- **synthesise's CROSS-STREAM SIGNALS section was substantive on
  both runs.** This was one of STEP-03's biggest open risks — the
  text-native equivalent of a typed schema field, where the model
  could skip the section if it didn't find interesting cross-stream
  patterns. The mandatory-section prompt instruction
  (*"The CROSS-STREAM SIGNALS section is mandatory — even if
  cross-stream patterns are weak, state that explicitly rather than
  skipping the section"*) appears to have done its job. Both runs
  produced specific, useful cross-stream analysis rather than
  boilerplate.

- **cross_check's RE-RESEARCH TARGETS reasoning was correct.** The
  fabricated Goldman Sachs note is news-shaped (an analyst forecast
  in a research note), so listing `news` as the right re-research
  target is the correct call. The auditor reasoned about *what kind*
  of fact the fabrication was and routed re-research accordingly.
  This is more sophisticated than just listing all streams; it's
  what Phase 1's typed Literal enum was meant to constrain but
  required code to interpret.

- **The cost of "skip preamble" parser logic just disappeared for
  tools-less specialists.** I'd been mentally budgeting for "every
  specialist needs preamble-tolerant parsing." The 0/4 result on
  tools-less specialists means six of the eight specialists need
  no preamble handling at all. The orchestrator's parser is
  smaller than I'd planned for.

## What's NOT decided yet

- **Whether the preamble hypothesis survives draft, revise,
  sense_check.** All three are tools-less. If they don't preamble,
  the hypothesis is robust. If they do, the explanation is
  different and the parser logic needs to be universal again.
- **Whether to extract input-assembly into a shared helper.**
  Right now each smoke test has its own `assemble_*_input`
  function. The orchestrator will eventually own this work, but
  if we keep multi-specialist smoke tests around (for partial
  chains), we may want a shared assembly module rather than
  duplicating the logic.
- **Whether the orchestrator should reuse smoke test patterns
  programmatically or just inspire its prompt.** Option (a) keeps
  Python assembly code reusable; option (b) trusts the orchestrator
  prompt to do it all. STEP-03's design was option (b); the smoke
  tests have shown option (a) is also viable. Worth revisiting when
  the orchestrator lands.

## Open questions

- **Cost shape at orchestrator scale.** ~3-6 cents per smoke run
  is fine. 10-15 cents per orchestrator end-to-end is fine. 20
  invocations a day during heavy development is $2-3. Still
  tractable, but worth tracking.

- **Will the auditor categories (consistency / calibration /
  grounding) earn their keep across more runs?** Both cross_check
  scenarios so far used the categories appropriately (grounding-only
  in the fail case). But two runs is a small sample. The discrimination
  matters most when issues are subtle — e.g., is a confidence
  mismatch a calibration issue or a grounding issue? Watch over
  more runs.

- **Synthesis CROSS-STREAM SIGNALS depth on weak days.** Both runs
  so far landed on days with rich material (active geopolitical
  crisis, major OPEC structural news). On a quiet day, will
  CROSS-STREAM SIGNALS still produce substantive content, or will
  the model fall back to "the streams are mostly consistent" boilerplate?
  Not testable until we hit a quiet day; logging the question.

## Glossary

- **Input assembly** — The work of packaging multiple upstream
  outputs into a single input string for a downstream specialist.
  In Phase 1 this happened automatically via shared state; in
  Phase 2 it's explicit, either in the orchestrator's prompt
  reasoning or in Python helper code.
- **VERDICT line** — Required opening line of an auditor's
  response (`VERDICT: PASS` or `VERDICT: FAIL`). The structural
  mitigation for audit-decision ambiguity introduced in STEP-03;
  validated in PR 3.
- **Live-chain smoke test** — A smoke test that exercises the full
  upstream chain rather than using hardcoded inputs. More
  expensive, more representative. Used for synthesise (one chain
  run, one synthesise call) and cross_check (one chain run, two
  cross_check calls with different synthesis inputs).
- **Fabrication injection** — A test pattern: take real upstream
  output, inject one specific known-bad claim, see whether the
  downstream auditor catches it. Stronger than handcrafted bad
  inputs and stronger than testing only the pass case.
- **Tool-equipped vs tools-less specialist** — The distinction that
  appears to correlate with preamble drift. Tool-equipped: research
  specialists. Tools-less: synthesise, the auditors, the renderers.
