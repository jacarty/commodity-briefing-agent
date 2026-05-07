# STEP-08 — Cross-check: the first auditor

## What I did

- Implemented `cross_check` — first node that drives graph control
  flow via conditional edges. Reads synthesis + all four research
  outputs; emits a `CrossCheckResult` with `passed: bool` plus three
  issue lists and a `re_research_targets` list of streams to re-run.
- Wired `route_after_cross_check` to read `cross_check_result.passed`
  and `cross_check_attempts`. Returns "passed" if synthesis is clean
  *or* if the retry cap is hit; "failed" otherwise.
- Defined `ResearchStream` as a top-level `Literal` type alias, used
  for `re_research_targets` so the schema can only contain valid
  stream names.
- Spent real time tightening the prompt after observing first-pass
  failures across multiple test runs.

## What I learned

### Two halves of the loop

Cross-check is the first node that makes the graph genuinely
agent-shaped. Before it, the graph is a pipeline — research, synth,
draft. Cross-check introduces conditional routing, which means the
graph has a real loop.

Two halves to wire correctly:

- **The node** writes structured judgement to state
- **The router** (a separate function passed to
  `add_conditional_edges`) reads state and returns a string, which
  the graph maps to a destination node

I'd not appreciated how cleanly LangGraph separates these. The node
doesn't know about routing; the router doesn't do work. Each half is
small and testable on its own.

### Retry caps prevent infinite loops

`route_after_cross_check` has two reasons to return "passed":

```python
def route_after_cross_check(state: State) -> str:
    if state["cross_check_result"]["passed"]:
        return "passed"
    if state["cross_check_attempts"] >= 2:
        return "passed"  # gave up, proceed anyway
    return "failed"
```

Without the cap, the graph could loop forever on synthesis the
auditor doesn't like. Two attempts is generous: first cross-check,
re-research, second cross-check, then commit to whatever's there.

The retry-cap pattern repeats for the sense-check / revise loop later.
Anywhere a graph has a feedback loop, it needs a way out.

### Pass-bias instructions are non-optional

First version of the cross-check prompt was a list of things to
check. First-pass failure rate was ~100% across three runs. The
auditor was finding "issues" everywhere — interpretive
disagreements, alternative readings, word choice preferences.

Added explicit pass-bias to the prompt: bias toward passing, only fail
on material issues, "would a competent reader reach a wrong
conclusion?" rather than "could this be phrased better?". Listed
specific things that are *not* cross-check issues (interpretive
preference, word choice, hedging-vs-commitment).

After tuning, first-pass failure rate dropped to ~33% on the same kind
of synthesis output. The remaining failures were the genuine cases —
synthesis inventing a support zone not in the research, dating
yesterday's events as today's, that kind of thing.

The lesson: auditor prompts have to bias toward passing or they
become noise. The bar for failure is structural, not editorial.

### Issues categorised by what re-research can fix

The schema has three issue lists rather than one:

- `consistency_issues` — synthesis fields contradict each other or
  contradict research
- `calibration_issues` — confidence in synthesis doesn't match
  confidence in research
- `grounding_issues` — claims in synthesis aren't supported by
  research

The categorisation matters because re-research can fix some types and
not others. Grounding issues often need new research. Consistency
issues might be resolved by re-running synthesis on the same research.
Calibration issues sit between.

In practice, re-research treats all flagged streams the same — feeds
the relevant issues back to the prompt for that stream and re-runs.
The categorisation is mostly editorial for now, but the structure is
in place if more sophisticated routing is ever wanted.

### `Literal` types as guardrails for downstream

`re_research_targets: list[ResearchStream]`. The `ResearchStream`
alias is `Literal["price", "news", "catalysts", "geopolitics"]`. The
schema validator only accepts those four exact strings.

Without this, cross-check could ask re-research to re-run "macro" or
"weather" — strings that look plausible but aren't valid streams.
Re-research would have to error or silently skip. With the Literal
constraint, the schema rejects bad targets at the source.

This is the same pattern as Literal enums in research outputs (STEP-05),
applied to inter-node communication. If a downstream node consumes
named values, constrain them at the schema level.

### Cross-check that fails consistently exposes synthesis problems

The first-pass failure cases are interesting. Cross-check repeatedly
flagged synthesis claims like "9 million bbl/d offline due to Hormuz"
when the research only said "Hormuz disruption" without the number,
or "$75-78 technical range" when no such range appeared in price
data.

Synthesis was inventing supporting detail. Cross-check found it
because synthesis is *checked against* research at the field level.

This is the agent self-correcting on a real failure mode. Without
cross-check, the brief would land confident-sounding numbers that
weren't in the research. The auditor catches this and forces the
correction. (Re-research, in STEP-09, gives synthesis better material
to work with on the second attempt.)

## What surprised me

- That the routing function is just a Python function returning a
  string. I expected more framework. The string maps to a destination
  via the dict passed to `add_conditional_edges`. No inheritance, no
  registration.

- How much the pass-bias instructions matter. Without them, the
  auditor confabulates issues to seem useful. With them, it largely
  passes synthesis that's actually fine.

- That cross-check finds genuine fabrications. I expected it to be
  pedantic. It's pedantic *and* it catches real synthesis problems.

## Open questions

- Could grounding issues be resolved without re-research, just by
  re-running synthesise on the existing research with the issues as
  context? Probably worth trying. For Phase 1, re-research handles
  all categories.

- Is two attempts the right cap? Three feels excessive for a daily
  brief; one would be too few. Two is the working answer; if cap-fired
  proceeding becomes common in practice, the answer is to fix
  upstream, not increase the cap.

## Glossary

- **Conditional edge** — Edge whose destination depends on a routing
  function reading state at runtime. The function returns a string;
  the destination is looked up in a dict passed when the edge is
  defined.
- **Retry cap** — A counter incremented each time a feedback loop
  fires. The router checks the counter and forces "proceed" when the
  cap is hit, preventing infinite loops.
- **Pass bias** — Auditor prompt strategy: only fail on material
  issues. Without it, auditors over-flag.
- **Auditor node** — A reasoner node whose job is to evaluate other
  nodes' output and route accordingly. Cross-check audits synthesis;
  sense-check (STEP-11) audits draft.
