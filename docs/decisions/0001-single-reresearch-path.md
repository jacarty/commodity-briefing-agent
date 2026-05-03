# ADR 0001 — Single re-research path from Cross-check

## Status

Accepted (Phase 1 design)

## Context

The graph design includes a Cross-check node that audits the synthesis
output and identifies issues. When issues are found, we re-research the
problematic streams and re-synthesise.

There were two reasonable topologies for this:

**Option A — Four return paths.** Cross-check identifies *which* research
stream had the problem (price, news, catalysts, or geopolitics) and the
conditional edge routes back to that specific research node. Most
surgical, lowest token waste, but four conditional return edges add
graph complexity.

**Option B — Single re-research path.** Cross-check writes a list of
flagged issues to a state field (`re_research_targets`). A single
"targeted re-research" node reads the field and re-runs whichever streams
need it. The conditional edge has one return path; the variability is
inside the re-research node.

## Decision

We use Option B — a single re-research node that reads
`re_research_targets` from state.

## Rationale

1. **Graph stays comprehensible.** Four return paths becomes hard to
   debug when a loop misbehaves. One return path is straightforward.

2. **Cost difference is negligible at this scale.** Re-running fine
   research wastes a few thousand tokens, well within budget.

3. **Cross-check fire rate is unknown.** Optimising the loop is
   premature without data on how often it actually fires. If it fires
   rarely, the optimisation is moot. If it fires every run, we have a
   different problem than topology.

4. **Migration path is open.** If Phase 2/3 data shows the
   four-return-path version would meaningfully reduce cost, the
   refactor is straightforward. The reverse — collapsing four return
   paths back to one — is harder.

## Consequences

- The re-research node has internal logic to dispatch to the right
  research operations based on `re_research_targets`. Its complexity
  goes up slightly.
- Cross-check's job is unchanged either way: identify what's wrong.
  Only the routing changes.
- If retry caps are hit, the loop exits regardless of whether all
  flagged issues were resolved. The cross-check result still gets
  written to state, so the draft stage can read it and surface
  unresolved issues if desired.

## Revisit if

- Production data (Phase 2/3) shows cross-check fires often enough
  that re-running unaffected streams is a measurable cost.
- The set of research streams grows beyond four (e.g., adding ETF
  positioning data), which would make the "single re-research" node
  harder to keep clean.