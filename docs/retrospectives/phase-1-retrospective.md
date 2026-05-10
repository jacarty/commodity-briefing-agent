# Phase 1 Retrospective

A blameless post-mortem isn't honest. This is the honest one. Some
mistakes were mine, some were Claude's, some were tooling — naming
each kind makes the retrospective useful for future me, and for
anyone else who builds an agent like this.

This is also a *Phase 1* retrospective, not a project retrospective.
The project as a whole is the same agent built on three architectures:

- **Phase 1**: LangGraph + Anthropic API direct (this one)
- **Phase 2**: Strands Agents on Bedrock AgentCore Runtime
- **Phase 3**: Vertex AI Agent Engine, Gemini

What follows is what I learned in Phase 1. Some of it is general
agent design; some of it is LangGraph-specific dressed as principle.
Phase 2 will tell us which is which. The retrospective should be
read as provisional: lessons recorded under one framework, awaiting
confirmation or contradiction in the next two.

Phase 1 shipped a working LangGraph commodity briefing agent: 12
nodes, two bounded feedback loops, schemas typed throughout, 35
tests, full end-to-end producing email-shaped output. It works.

---

## What worked (in Phase 1)

### State-first design
The single most consequential choice. Designing the State schema
in step 03 before writing any nodes meant every node was small.
The conceptual mistakes (operational vs audit, who writes what,
when fields get cleared) got caught at the design stage where they
were cheap to fix.

If I'd dived into nodes first, I'd have spent the project
retrofitting state shape around emergent needs.

**Provisional**: state-first might be a real principle, or it might
be that LangGraph's StateGraph forced me to think about state
upfront and the design benefited as a side effect. Phase 2 will
show whether Strands has a similar primitive that drives this kind
of thinking — or whether the design fragments without it.

### Schema-as-contract everywhere
Every LLM call uses `with_structured_output` against a TypedDict.
Every research output, audit result, and rendered brief is
schema-typed. JSON-parsing problems I expected to debug never
materialised.

The exception that proved the rule: `create_agent` + Anthropic
server-side tools + `response_format` is fragile. Once we moved
off it, the fragility went away.

**Provisional**: schema-as-contract may be portable as a *principle*
(define what each step produces, enforce it at the model layer),
but the mechanism — `with_structured_output` against a TypedDict —
is LangChain-specific. Bedrock's tool-use API and Vertex's function
calling each have their own ergonomics. Phase 2 will tell us
whether the pattern survives without the LangChain abstraction
smoothing it out.

### Bounded loops with retry caps
Two feedback loops, both bounded by retry caps with safety-valve
routes. The retry caps fired in practice multiple times during
testing — exactly when they were supposed to. The graph never
infinite-looped.

**Likely portable**: this lives at the routing level, not the
framework level. Any agent framework with conditional flow can
implement retry caps. If Phase 2 makes it harder than this, that's
a finding about Strands, not about the principle.

### Coach-first, code-second
Every step started with design discussion. The two times I
deviated — the news flakiness migration and the cleanup chore both
deferred too long — were the two times I paid the deferred cost.

**Portable**: this is a meta-lesson about how I work, not about the
architecture. Carries forward to Phase 2 unchanged.

---

## What didn't work, and whose fault

### `create_agent` flakiness — Claude's pattern recommendation aged poorly
Claude recommended `create_agent` for news in step 05. I shipped
it. The pattern is fragile in a specific way (LLM emits valid JSON
for the schema, then keeps generating commentary, parser sees
"Extra data" and fails) that's probabilistic — passes most of the
time, fails occasionally.

Claude flagged the pattern as fragile during the catalysts step
when the failure mode first manifested. We migrated catalysts.
We did *not* migrate news at the same time, even though the same
failure mode was predicted. News kept passing tests for several
more PRs. Then in step 12 (deliver), news finally produced the
failure mode, blocking the PR.

This is a shared failure. Claude should have pushed harder for the
preventative migration. I should have heard "the same pattern
elsewhere is fragile" and fixed news while the catalysts pattern
was fresh. Both of us defaulted to "it's working, leave it" when
the rational move was "it's going to fail, fix it now."

Lesson for next time: when the same failure mode is predicted in
multiple places and one instance has manifested, fix the others
preemptively, not when they fail in production.

### Cross-check over-flagging on first prompt — prompt design
The first version of cross-check failed every synthesis on first
pass. Took two prompt iterations to land on the right pass-bias
instructions: explicit list of what is NOT a cross-check issue,
"would a competent reader reach a wrong conclusion" framing.

Lesson: auditor prompts need pass-bias from day one. Drafting an
auditor prompt without it is naive — the model defaults to finding
things to flag because that's what it thinks helpfulness looks like.

This lesson likely ports unchanged to Phase 2. The pass-bias
problem is about LLM behaviour, not framework wiring.

### Synthesis sometimes fabricates supporting detail — partly addressed
Synthesis would occasionally invent specific numbers ("$75-78
support zone") or mis-date events that weren't in the research.
Cross-check catches this; re-research forces correction.

Status: acceptable for Phase 1. The loop catches it. If
fabrication-rate becomes a problem, tighten synthesis's prompt
before adding more auditor logic.

This is a known LLM failure mode that Phase 2 will inherit. Worth
watching whether Bedrock-hosted Claude has the same fabrication
tendency or whether something about the routing layer reduces it.

### Confidence ratings collapse in synthesis
Geo emits themes with calibrated confidence ratings. Synthesis
sometimes ignores the calibration and produces uniformly committed
prose. The auditor's calibration_issues category catches this.

Status: same as fabrication. Acceptable, the loop catches it.

---

## Process mistakes

### Linter setup deferred until PR 12
I should have set up Ruff and pre-commit at PR 1, not PR 12. By
the time the linter landed, the codebase had:

- Inconsistent blank-line counts between top-level definitions
- Trailing whitespace on indented blank lines
- Mixed comma conventions in multi-line calls
- A self-import in `nodes.py` that wasn't a real dependency

Each is small. Together they're noise.

Lesson: Ruff + pre-commit + CI is small enough to be PR 1, not
something to add later. Baseline tooling is part of project setup.

**Direct action for Phase 2**: linter and CI from PR 1, no
exceptions.

### Tests-against-real-APIs decision not documented
Throughout the project, tests hit real APIs. This was a deliberate
choice — contract tests verify shape end-to-end, including
provider-level behaviour. Mocks would just verify the mocks.

But this choice was never written down. Future-me running tests
six months from now might assume mocks are missing and add them.
That would be backsliding.

Lesson: design choices that diverge from default expectations need
to be documented in `CLAUDE.md` or equivalent.

**Direct action for Phase 2**: document this in Phase 2's
`CLAUDE.md` from day 1, plus the cost note (Bedrock per-call costs
differ from Anthropic-direct, so the same philosophy might need
different cadence).

### Some test failure modes were diagnosed wrong on first attempt
When the news node first hung in tests, Claude jumped to a
hypothesis (cross-test interaction or rate limiting) that turned
out to be wrong. The actual cause was the `create_agent` fragility.
The fix took five minutes once we got there; the misdirection took
about thirty.

Lesson: when an LLM-pair-programmer offers a hypothesis, ask it to
enumerate alternatives before acting. The first hypothesis is often
the most pattern-matched, not the most accurate.

---

## Where Claude over-claimed

This deserves its own section.

Twice in this project, Claude was confidently wrong about
LangChain internals:

1. Claude claimed `nodes.py` had `research_catalysts` defined
   twice. It didn't.

2. Claude claimed that `bind_tools + with_structured_output`
   stacked together would have edge-case problems similar to
   `create_agent`. It doesn't — the pattern works cleanly.

Both times, the test results corrected the hypothesis. The pattern:
Claude pattern-matches confidently; the test suite is ground
truth; trust the test suite.

Lesson for next time: when Claude offers a confident claim about
how a library or framework behaves, verify it empirically before
acting.

This will matter even more in Phase 2. Strands is newer than
LangGraph, has less training data behind it, and Claude's
pattern-matching will be weaker. Empirical verification will need
to happen earlier and more often.

---

## What the project is actually about

This is the section worth highlighting now that Phase 1 is one
implementation rather than the project.

The interesting question across all three phases is: **how much of
what I learned in Phase 1 is about agent design, and how much is
about LangGraph?**

The "what worked" section above claims state-first design and
schema-as-contract as core principles. They might be. They might
also be patterns that LangGraph happens to make natural, which I
mistook for principles.

Phase 2 (Strands + AgentCore) is where this gets tested. If
state-first design feels equally natural in Strands, it's a
principle. If Strands' shape resists it and the resulting design
is still good, the principle was over-stated. If Strands resists
it and the resulting design is worse, the principle was real and
LangGraph was the right framework for it.

Phase 3 (Vertex Agent Engine) is the second confirmation. If a
pattern survives both Strands and Vertex, it's portable. If it
only survives one, the framework matters.

The retrospective lessons should be re-read after each phase with
this question in mind.

---

## What carries into Phase 2

### Design assets that copy across
- The conceptual node decomposition (12 nodes, 4 research streams,
  2 bounded loops)
- The prompts (markdown files, copied verbatim, adjusted only if
  Bedrock-Claude behaviour differs)
- The schemas in spirit (field names, field meanings, Literal enum
  values stay constant; the implementing TypedDicts may not)
- The end-to-end test fixtures
- This retrospective's process lessons (Ruff from day 1, CLAUDE.md
  from day 1, model-factory abstraction from day 1)

### What gets rebuilt
- Every line of framework code (graph, nodes, state, all of it)
- Tool definitions (Anthropic server-side web_search → Tavily or
  AgentCore equivalent)
- State management (StateGraph → Strands' primitive)
- Conditional routing
- Deployment harness (Lambda + SES → AgentCore Runtime)

### What I'm watching for
- Whether the same architecture diagram describes Phase 2's agent.
  If not, that divergence is itself a finding.
- Whether two-stage analyse-then-render survives. The most
  interesting principle to test.
- Whether Strands pushes the design toward more agent-loop-shaped
  nodes than LangGraph did.
- Whether Bedrock's structured-output mechanism is as reliable as
  LangChain's `with_structured_output`. If it's not, the patterns
  may need to change.

---

## Phase 1 in numbers

- **PRs**: ~12 feature PRs, plus 1 chore PR, plus the docs PR
- **Lines of code**: ~750 (nodes), ~50 (graph), ~25 (state),
  ~150 (prompts as markdown), ~600 (tests). Roughly 1,500 total.
- **Tests**: 35, all against real APIs
- **Test runtime**: ~3 minutes for the full suite
- **Schemas defined**: 11 TypedDicts
- **Loops**: 2 (cross-check / re-research, sense-check / revise),
  both bounded at 2 attempts

A complete LangGraph agent in ~1,500 lines is a meaningful
demonstration that the framework absorbs orchestration well. Most
of the volume is prompts and tests. The actual graph wiring is
small.

Phase 2 should produce a comparable agent on Strands. If it ends
up substantially larger or smaller in line count, that ratio is
itself informative — it tells us whether Strands' abstractions are
more or less weight than LangGraph's for this kind of work.

---

## Final principle, restated

The goal of Phase 1 was to learn LangGraph by building something
useful. That goal is met.

The goal of the *project* is to learn whether the conceptual design
of an agent — the patterns named in the tutorials and lessons named
in this retrospective — actually generalise across architectures.

Phase 1 produces the hypothesis. Phases 2 and 3 test it.
