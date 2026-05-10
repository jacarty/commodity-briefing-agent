# STEP-09 — Re-research: closing the loop

## What I did

- Implemented `re_research` — the node that gives the cross-check loop
  teeth. Reads `re_research_targets` and `cross_check_result` from
  state; runs the relevant research nodes again with feedback baked
  into the prompt.
- Added `research_feedback: dict` to State so feedback can flow from
  re-research back into the research nodes.
- Modified `research_news`, `research_catalysts`, `research_geo` to
  read optional feedback from state and include it in their prompts.
  Default to empty when not in re-research mode.
- Built a `RESEARCH_FUNCTIONS` dict mapping stream names to functions.
  `price` is excluded — it's deterministic; there's nothing for an
  LLM-driven re-research to fix.
- Verified end-to-end: a cross-check failure on first pass triggers
  re-research, second-pass synthesis uses the new research, second
  cross-check passes.

## What I learned

### Feedback flows via state, not function signatures

Re-research could have called the research functions with extra
arguments:

```python
# Could have done this — didn't.
research_news(state, feedback="...")
```

Instead, feedback is added to state and the research functions read
it from state:

```python
feedback = state.get("research_feedback", {}).get("news", "")
```

Reasons:

- Research function signatures stay uniform with all other nodes
  (state in, dict out). No special branching for "called normally" vs
  "called by re-research."
- State is already the agent's communication channel. Adding a new
  field is the established pattern.
- Default to empty string means the same research function works for
  first-pass and re-research without conditional logic.

The pattern: any time downstream behaviour needs to change based on
upstream context, route the context through state, not through
arguments.

### Sequential, not parallel

Cross-check might flag two streams at once. Re-research could run
them in parallel using LangGraph's fan-out support. Sequential is
simpler and the latency cost is negligible for a daily-run agent.

```python
for target in targets:
    if target not in RESEARCH_FUNCTIONS:
        continue
    result = RESEARCH_FUNCTIONS[target](enriched_state)
    updates.update(result)
```

Don't pre-optimise. If re-running two streams ever becomes a
bottleneck, parallelisation is a contained refactor.

### Skipping price is silent and correct

Cross-check can list "price" in `re_research_targets`. Re-research
checks whether the target is in `RESEARCH_FUNCTIONS` (which doesn't
include price). If it isn't, the loop continues to the next target.
No print, no error.

The first time this happens in a real run is striking — the trace
shows `re_research_targets: ['price', 'news']` but only news
re-runs. That's the design working: price is deterministic data;
there's nothing to "re-research." Including it in the targets is
fine because the schema allowed it; skipping it at execution is the
right behaviour.

### Filtering issues by stream is heuristic

`_format_feedback` builds the per-stream feedback by filtering the
flat issue lists for ones that mention the stream by name:

```python
relevant = [i for i in issues if stream.lower() in i.lower()]
```

This is a substring match, not structured. It works because
cross-check tends to mention the stream name in its issue text ("News
stream missed source X"). It would fail if cross-check produced
generic issues like "this claim is unsourced."

For Phase 1, this is good enough. The structured alternative would be
making cross-check's issue lists themselves typed by stream — each
issue tagged with which stream it relates to. That's the right design
if filtering ever becomes unreliable. For now, the heuristic holds.

### The loop closes meaningfully

End-to-end: a real run where cross-check fails, then passes after
re-research, looks like this:

- First synthesis claims a "9 million bbl/d gap" stated as fact
- Cross-check flags this as ungrounded
- Re-research re-runs news and geo with the feedback
- Second pass: same general thesis survives, but the 9 mbd figure
  now appears with proper attribution to the news source
- Second cross-check passes

The fix wasn't that the model abandoned the claim. The model went and
*found* the source for it. That's a real improvement in the brief's
honesty — same conclusion, properly grounded. The loop did real work.

This is when the cross-check + re-research pair earns its complexity.
Cross-check alone would just be a fail signal. Re-research alone has
nothing to address. Together they form a self-correcting cycle.

### Clearing operational state matters

```python
updates["re_research_targets"] = []
```

After re-research runs, it clears the targets. If it didn't, the
next cross-check would see stale targets and the wrong thing would
happen on the next loop iteration.

This is the operational-vs-audit principle from STEP-03 in practice.
`re_research_targets` is operational — it tells re-research what to
do *next*. Once consumed, it should be cleared. Audit fields would
append; operational fields replace, including replacing with empty.

I left `research_feedback` populated for traceability, but the
targets specifically need to clear.

## What surprised me

- That changing only the research outputs (without changing the
  synthesis prompt) is enough to fix synthesis problems. Synthesis
  isn't malicious; it's working from inputs. Better inputs produce
  better synthesis automatically.

- How much of the work is in `_format_feedback` — building a clear,
  stream-specific instruction from cross-check's flat issue lists.
  The function looks small but the design is load-bearing.

- That the empty-targets early return is needed at all. The router
  shouldn't send anything to re-research without targets, but
  defensive coding here is cheap insurance against router bugs.

## Open questions

- Should re-research itself be idempotent? Right now if cross-check
  fails twice, re-research runs twice with potentially overlapping
  feedback. Not a problem in practice, but worth thinking about if
  retry caps ever increase.

- Could `research_feedback` carry richer structure (per-issue, with
  category) rather than free-form strings? Possibly. The free-form
  string is what the LLM consumes; pre-structuring it forces a
  serialisation step that may not buy much.

## Glossary

- **Operational state** — Fields that drive next-step behaviour.
  Should be cleared after consumption. `re_research_targets` is the
  classic example.
- **Self-correcting loop** — A feedback cycle where audit findings
  produce material change in the underlying work. Cross-check +
  re-research together; sense-check + revise (STEP-11) similarly.
- **`RESEARCH_FUNCTIONS` dict** — Maps stream names to research node
  functions. The lookup is what makes re-research generic across
  streams. Excludes `price` because price isn't LLM-driven.
