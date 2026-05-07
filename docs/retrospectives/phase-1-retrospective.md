# Phase 1 Retrospective

A blameless post-mortem isn't honest. This is the honest one. Some
mistakes were mine, some were Claude's, some were tooling — naming
each kind makes the retrospective useful for future me, and for
anyone else who builds an agent like this.

Phase 1 shipped a working LangGraph commodity briefing agent: 12
nodes, two bounded feedback loops, schemas typed throughout, 35
tests, full end-to-end producing email-shaped output. It works.
What follows is what I'd do differently next time.

---

## What worked

### State-first design
The single most consequential choice. Designing the State schema
in step 03 before writing any nodes meant every node was small.
The conceptual mistakes (operational vs audit, who writes what,
when fields get cleared) got caught at the design stage where they
were cheap to fix.

If I'd dived into nodes first, I'd have spent the project
retrofitting state shape around emergent needs. I've seen this
fail. Doing it the other way around takes a one-step diversion at
the start; it pays off across every subsequent step.

### Schema-as-contract everywhere
Every LLM call uses `with_structured_output` against a TypedDict.
Every research output, audit result, and rendered brief is
schema-typed. This eliminated a class of failure I expected to
spend significant time on (JSON parsing, output validation, "the
model didn't return what I asked for" debugging). Nearly none of
that materialised.

The exception that proved the rule: `create_agent` + Anthropic
server-side tools + `response_format` is fragile in a specific
way. Once we moved off it for everything except news, the fragility
went away. When we eventually moved news off it too, the last
known failure mode disappeared.

### Bounded loops with retry caps
Two feedback loops, both bounded by retry caps with safety-valve
routes. The retry caps fired in practice multiple times during
testing — exactly when they were supposed to. The graph never
infinite-looped. The bound was always honoured.

### Coach-first, code-second
Every step started with design discussion. Schemas agreed before
code, prompts drafted before nodes, loops diagrammed before
edges wired. This was faster than diving into code, because
conceptual mistakes are caught at the design stage.

The two times I deviated — the news flakiness migration and the
cleanup chore both deferred too long — were the two times I paid
the deferred cost.

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
failure mode in a test run, blocking the PR.

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
pass. The auditor was finding "issues" that were really
interpretive disagreements, alternative phrasings, or hedging
preferences.

Took two prompt iterations to land on the right pass-bias
instructions. The fix was structural (explicit list of what is NOT
a cross-check issue, "would a competent reader reach a wrong
conclusion" framing), not cosmetic.

Lesson: auditor prompts need pass-bias from day one. Drafting an
auditor prompt without it is naive — the model defaults to
finding things to flag because that's what it thinks helpfulness
looks like.

### Synthesis sometimes fabricates supporting detail — partly addressed
Synthesis would occasionally invent specific numbers ("$75-78
support zone") or mis-date events that weren't in the research.
Cross-check catches this; re-research forces correction.

This is the agent self-correcting on a real failure mode, which
is good. But it means synthesis is doing work the prompt
discourages but doesn't eliminate. Stronger anti-fabrication
prompts on synthesis itself would reduce the load on the auditor.

Status: acceptable for Phase 1. The loop catches it. If
fabrication-rate becomes a problem in production, tighten
synthesis's prompt before adding more auditor logic.

### Confidence ratings collapse in synthesis
Geo emits themes with calibrated confidence ratings. Synthesis
sometimes ignores the calibration and produces uniformly committed
prose. The auditor's calibration_issues category catches this when
it does.

Could be addressed with stronger "preserve research confidence
ratings" instructions in the synthesis prompt. Status: same as
above — acceptable, the loop catches it, fix if it becomes a
problem.

---

## Process mistakes

### Linter setup deferred until PR 12
I should have set up Ruff and pre-commit at PR 1, not PR 12. By
the time the linter landed, the codebase had:

- Inconsistent blank-line counts between top-level definitions
- Trailing whitespace on indented blank lines
- Mixed comma conventions in multi-line calls
- A self-import in `nodes.py` that wasn't a real dependency

Each is small. Together they're noise. If the linter had been there
from PR 1, the cleanup PR wouldn't have existed and the noise
would never have accumulated.

Cost: a cleanup, plus the friction of reading
inconsistently-formatted code during development.

Lesson: Ruff + pre-commit + CI is small enough to be PR 1, not
something to add later. Baseline tooling is part of the project
setup, not an after-thought.

### Tests-against-real-APIs decision not documented
Throughout the project, tests hit real APIs (Anthropic, yfinance).
This was a deliberate choice — the contract tests verify shape
end-to-end, including provider-level behaviour. Mocks would just
verify the mocks.

But this choice was never written down. Future-me running tests
six months from now might assume mocks are missing and add them.
That would be backsliding.

Lesson: design choices that diverge from default expectations need
to be documented in `CLAUDE.md` or equivalent. "We don't mock the
LLM in tests because [reasons]" is a one-line statement that saves
future-me an hour.

### Some test failure modes were diagnosed wrong on first attempt
When the news node first hung in tests during catalysts
development, Claude jumped to a hypothesis (cross-test interaction
or rate limiting) that turned out to be wrong. The actual cause
was a known fragility in `create_agent` + structured output. The
fix took five minutes once we got there; the misdirection took
about thirty.

I should have asked Claude to consider multiple hypotheses before
acting on the first one. Or: I should have run a simpler
diagnostic (single test in isolation) before agreeing with the
proposed cause. Either intervention would have shortened the
debugging.

Lesson: when an LLM-pair-programmer offers a hypothesis, ask it
to enumerate alternatives before acting. The first hypothesis is
often the most pattern-matched, not the most accurate.

---

## Where Claude over-claimed

This deserves its own section.

Twice in this project, Claude was confidently wrong about
LangChain internals:

1. Claude claimed `nodes.py` had `research_catalysts` defined
   twice. It didn't. The hypothesis was based on misreading the
   pasted file. I had to verify by reading the file myself.

2. Claude claimed that `bind_tools + with_structured_output`
   stacked together would have edge-case problems similar to
   `create_agent`. It doesn't — the pattern works cleanly. We
   only knew because I ran the tests and they passed.

Both times, the test results corrected the hypothesis. The pattern:
Claude pattern-matches confidently; the test suite is ground
truth; trust the test suite.

Lesson for next time: when Claude offers a confident claim about
how a library or framework behaves, verify it empirically before
acting. Hypothesis is cheap; the framework's actual behaviour is
authoritative.

This is a real failure mode of LLM-pair-programming, not a
specific failing of this project. Naming it lets future-me notice
the pattern earlier.

---

## What would change for Phase 2

Phase 2 is the same agent on Bedrock with AgentCore Runtime,
Claude via Bedrock instead of direct Anthropic.

Expected migration items:

- Model name strings change (`claude-haiku-4-5` →
  Bedrock-prefixed identifier)
- Web search tool changes — Anthropic server-side `web_search` is
  not available on Bedrock. Tavily will be used as a Python tool
- Environment variables — `ANTHROPIC_API_KEY` becomes AWS
  credentials
- Deployment harness — Lambda + AgentCore Runtime instead of
  whatever Phase 1 hosting would have been

Things that should not change:

- State schema
- Node functions (modulo the model-factory abstraction needed for
  the Bedrock client)
- Prompts
- Schemas
- Tests (the contracts hold; only the underlying provider changes)

If the design is right, the migration should be mostly
configuration. We'll find out in Phase 2.

### Things to do better in Phase 2

1. Linter and CI from PR 1, not PR 12. Inherit the chore PR's
   tooling forward.
2. `model_factory` abstraction from PR 1. Per-call `ChatAnthropic`
   instantiation is fine for Phase 1; for a multi-provider
   project it becomes a real problem.
3. Document the test-philosophy choice in `CLAUDE.md` from the
   start.
4. When Claude offers a hypothesis about framework internals, ask
   for alternatives and verify empirically.
5. When the same pattern manifests a failure mode in two places,
   fix the third place preemptively.

---

## Phase 1 in numbers

- **PRs**: ~12 feature PRs, plus 1 chore PR
- **Lines of code**: ~750 (nodes), ~50 (graph), ~25 (state),
  ~150 (prompts as markdown), ~600 (tests). Roughly 1,500 total.
- **Tests**: 35, all against real APIs
- **Test runtime**: ~3 minutes for the full suite
- **Schemas defined**: 11 TypedDicts (research outputs, audit
  results, brief structure, final brief)
- **Loops**: 2 (cross-check / re-research, sense-check / revise),
  both bounded at 2 attempts
- **Time elapsed**: project spans roughly the duration of the
  development conversations

A complete LangGraph agent in ~1,500 lines is a meaningful
demonstration that the framework absorbs orchestration well. Most
of the volume is prompts (in markdown) and tests (legitimately
needed). The actual graph wiring is small.

---

## Final principle

The goal of Phase 1 was to learn LangGraph by building something
useful. Both halves matter: "learn LangGraph" means engaging with
the patterns deliberately, not just shipping; "something useful"
means a real working agent, not a toy.

The agent is real. The patterns are now familiar. Phase 2 should
go faster because the foundation holds.
