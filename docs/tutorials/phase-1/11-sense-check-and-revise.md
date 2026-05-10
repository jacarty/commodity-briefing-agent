# STEP-11 — Sense-check and Revise: prose-level audit

## What I did

- Implemented `sense_check` — second auditor in the graph. Reads
  synthesis and the four draft sections; emits a `SenseCheckResult`
  with `passed: bool`, four issue lists, `revision_notes`, and a
  summary.
- Implemented `revise` — produces an updated `Brief` given the
  current draft, the synthesis (source of truth), and the sense-check
  feedback.
- Wired the second conditional edge: `route_after_sense_check` mirrors
  the cross-check router. Same retry cap of 2.
- Reused the `Brief` schema for revise's output. Same shape as
  draft, different content.

## What I learned

### Two auditors, two different layers

Cross-check audits structured analysis: "does this synthesis match
the research?" Sense-check audits prose: "does this brief match the
synthesis it was meant to render?"

A draft can faithfully render synthesis and still produce bad prose.
Sections might be redundant, headline metrics might be missing,
voice might drift. Cross-check can't see any of this — it's reading
structured data, not the rendered output.

The distinction matters because each auditor has its own failure
mode and its own fix. Cross-check failures lead to re-research.
Sense-check failures lead to re-drafting. The two loops are
parallel, not sequential.

### Faithfulness as the primary check

Sense-check has four issue categories:

- `faithfulness_issues` — does the brief match what synthesis said?
- `structure_issues` — sections distinct, metrics present, sections
  the right length?
- `prose_issues` — bullets, headers, weasel phrases, voice drift?
- `consistency_issues` — does the brief contradict itself across
  sections?

Faithfulness is the headline category. The most consequential
failure mode is a brief that *sounds* confident but says something
different from what synthesis concluded. Synthesis hedged on China
demand; brief states it flat. Synthesis identified Y as dominant;
brief leads with X.

The other categories matter, but they're secondary. A brief with
some bulleted prose is annoying; a brief that misrepresents the
analysis is dangerous.

### `revision_notes` is operational state for revise

Sense-check writes a `revision_notes` string when it fails. Revise
reads it and acts on it. The revise prompt threads it directly into
the prompt as the "issues to address" section.

Same pattern as `re_research_targets` in STEP-09: auditor produces
operational instruction; downstream node consumes it. State is the
channel.

The instruction has to be specific. Generic "improve the prose"
gives revise nothing to act on. Sense-check's prompt explicitly
demands actionable feedback: "the news section opens with the SPR
release; lead with OPEC+ fragmentation instead, since synthesis
identified that as the structural story."

Output quality of revise is largely determined by output quality of
sense-check. Auditor prompts shape downstream behaviour.

### Revise is targeted re-rendering, not rewriting

Revise's prompt: "Address each flagged issue specifically. Keep the
original tone and structure for sections that weren't flagged."

Revise should not be a fresh draft attempt. The original draft was
mostly fine; revise fixes the flagged parts. This minimises drift.

In practice, sense-check failures during testing have been rare — the
brief usually passes first time. When revise does fire, the second
draft retains most of the first and fixes the specific issue.

### Same retry cap, same reasoning

`route_after_sense_check` has the same shape as
`route_after_cross_check`: pass on `passed: True`, pass on retry cap
hit, otherwise fail.

```python
def route_after_sense_check(state: State) -> str:
    if state["sense_check_result"]["passed"]:
        return "passed"
    if state["sense_check_attempts"] >= 2:
        return "passed"
    return "failed"
```

The reasoning from STEP-08 applies: bounded loops or infinite loops.
Two attempts is generous; if a second pass still fails, the issue is
likely in synthesis, not the prose, and revise can't fix it.

### Sense-check passes more often than cross-check

Empirically: sense-check passes first time on most runs. Cross-check
is more frequently triggered. This makes sense:

- Synthesis is doing analytical work — it can over-claim, conflate
  research, fabricate
- Draft is mostly rendering — synthesis already did the editorial
  work, and the prompt's strong constraints prevent format drift

The two-stage analyse-then-render split, established in STEP-10, pays
off here. Most prose problems are absent because synthesis already
handled the editorial work. Sense-check mostly verifies, rarely
catches.

If the architecture were one-stage (synthesise-and-draft together),
sense-check would have to do much more.

## What surprised me

- That sense-check usually passes on first try. I expected the prose
  layer to need more iteration. The synthesis-then-draft separation
  is doing more work than I gave it credit for.

- That `revise` is mostly idle code. It's written; it works; it
  rarely fires. Acceptable — the loop infrastructure is needed for
  the cases where it does, and absent cost when it doesn't.

- How small the conditional-edge code is. Two router functions, each
  three lines. The graph framework absorbs the rest. Compared to a
  hand-written workflow with similar branching, this is genuinely
  less code.

## Open questions

- Could sense-check and cross-check share a base prompt structure?
  They have similar shape (auditor with categorised issues, pass-bias
  guidance). Probably not worth abstracting — the categories differ
  and the prompts are short enough.

- Is revise underused? If sense-check rarely fires, revise rarely
  fires. Could revise be combined with draft into a "draft with
  feedback" node that handles both first-pass and revision? Would
  save one node at the cost of conditional logic in the function.

## Glossary

- **Faithfulness check** — Auditor concept: does the rendered output
  match the source analysis it claims to render? The most important
  thing sense-check checks.
- **Targeted re-rendering** — Revise's job. Fix specific flagged
  issues without rewriting unflagged sections. Distinguished from
  a full re-draft.
- **Two-stage analyse-then-render** — Architectural pattern:
  separate the analytical work (synthesise) from the rendering
  (draft). Lets each stage be audited at its own level by a
  dedicated auditor.
