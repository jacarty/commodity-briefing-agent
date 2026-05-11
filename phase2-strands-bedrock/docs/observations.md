## 2026-05-11 — cross_check pass-bias and detection both work first try

**Observed**: Two cross_check smoke scenarios in one run.

Scenario 1: clean synthesis from a full live chain. Result:
`VERDICT: PASS`, all four issue sections "None.", no
re-research requested.

Scenario 2: same synthesis with a fabricated Goldman Sachs $147
oil forecast injected into HEADLINE METRICS. Result:
`VERDICT: FAIL`, GROUNDING ISSUES explicitly named the
fabrication and identified its location ("does not appear in any
of the four research streams"). RE-RESEARCH TARGETS listed `news`
as the right stream to re-run, because the fabricated claim is
analyst-forecast-shaped and news is where such claims would land.

**What we did**: Nothing. Both behaviours were what we hoped for.

**Implication**: Three pieces of STEP-03's design validated in
one run:

1. **The VERDICT: PASS/FAIL line works.** First-line determinism
   without breaking text-native. Both runs led with it cleanly.
2. **Pass-bias prompts port verbatim from Phase 1.** The auditor
   didn't over-flag the legitimate synthesis. Phase 1's
   prompt-engineering lesson holds in Strands.
3. **Issue categorisation has real value.** The auditor explicitly
   separated grounding from consistency from calibration — flagging
   grounding-only when the other categories were genuinely fine.
   This is the discrimination Phase 1 designed the categories for,
   and it transferred unchanged.

The orchestrator can rely on the VERDICT line as the routing
signal and on RE-RESEARCH TARGETS as the next-action signal,
both as designed.

---

## 2026-05-11 — Preamble-drift hypothesis confirmed (2/2 tools-less specialists clean)

**Observed**: cross_check, like synthesise, opened with the
required structural marker on the first line (`VERDICT: PASS` /
`VERDICT: FAIL`) — no preamble. Both runs.

Standing count across the four specialists built so far:
- research_news (tool-equipped): preamble 3/3
- research_catalysts (tool-equipped): preamble 2/2
- research_geo (tool-equipped): preamble 2/2
- synthesise (tools-less): preamble 0/2
- cross_check (tools-less): preamble 0/2

7/7 with tools, 0/4 without. The pattern holds at 11 runs across
five specialists.

**What we did**: Nothing. Hypothesis confirmed.

**Implication**: The orchestrator's parser only needs leniency
about leading content for the four tool-equipped research
specialists. For the other six (synthesise, the two auditors,
draft, revise), parsers can read strictly from the first
character.

This is a meaningful simplification. The parser logic for
auditors specifically — read the VERDICT line, route on PASS or
FAIL — can be a simple regex on line 1, not a "skip preamble
then look for VERDICT" scan.

Will re-test the hypothesis once draft and revise land (both
tools-less). If they preamble, the explanation is more nuanced
than "tools vs no tools" and the parser logic needs to be
universal again.
