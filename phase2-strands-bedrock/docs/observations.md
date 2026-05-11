## 2026-05-11 — Orchestrator happy-path works end-to-end on first run

**Observed**: First end-to-end smoke run of the orchestrator
completed without intervention. The orchestrator:

1. Called `fetch_price`
2. Called `research_news`, `research_catalysts`, `research_geo`
3. Called `synthesise` with research outputs assembled
4. Called `cross_check`, got `VERDICT: PASS`, proceeded
5. Called `draft`
6. Called `sense_check`, got `VERDICT: PASS`, proceeded
7. Produced FinalBrief as structured output (3 fields, all populated)

Nine tool calls, no retries, structured output validated. Brief
is editorially strong (specific numbers, real entities, inverted
pyramid, no bullets, no internal headers — Phase 1's editorial
discipline intact end-to-end).

**What we did**: Nothing. Smoke run worked.

**Implication**: Two STEP-03 open questions answered positively:

- **Input-string assembly works.** The orchestrator packaged
  upstream outputs into coherent inputs for synthesise,
  cross_check, draft, and sense_check. If assembly had been
  broken, the audits would have failed.
- **VERDICT line interpretation works.** The orchestrator read
  `VERDICT: PASS` from both audits and proceeded as designed.

The declarative-goal-and-constraints style of orchestrator prompt
(STEP-03's Q1=b) was sufficient on the first run. No imperative
recipe needed.

---

## 2026-05-11 — Orchestrator dropped "SECTION" from final brief headers

**Observed**: The orchestrator's FinalBrief.plain_text_body uses
the headers `PRICE / NEWS / CATALYSTS / GEOPOLITICS` rather than
the `PRICE SECTION / NEWS SECTION / CATALYSTS SECTION /
GEOPOLITICS SECTION` headers that draft and revise produce
internally.

This is a small formatting choice the orchestrator made when
repackaging the approved draft into the structured output.
Probably fine for an end deliverable (the word "SECTION" is more
useful as an internal-pipeline marker than an end-user header),
but it's an inconsistency.

**What we did**: Nothing. Logged.

**Implication**: Two ways to read this:

- **Acceptable normalisation**: end-user briefs don't need the
  word "SECTION" in their headers; this is editorial polish the
  orchestrator added on its own.
- **Drift to avoid**: the orchestrator should pass the approved
  brief through verbatim and not normalise headers.

The orchestrator prompt currently says *"the FinalBrief renders
the *approved* brief"* — which could be read either way. Could
tighten with explicit "preserve the exact section headers as
they appear in the approved draft" if we wanted strict
pass-through. For now, fine.

A small thing, worth being aware of for the eventual
retrospective.

---

## 2026-05-11 — cross_check retry-cap enforcement works under failure

**Observed**: Failure-path smoke test with a stubbed cross_check
that always returns `VERDICT: FAIL`. The orchestrator's tool-call
trace:

```
Tool #1:  fetch_price
Tool #2:  research_news
Tool #3:  research_catalysts
Tool #4:  research_geo
Tool #5:  synthesise
Tool #6:  cross_check       ← cycle 1, FAIL
Tool #7:  research_news     ← acted on RE-RESEARCH TARGETS
Tool #8:  synthesise        ← re-synthesise with new news
Tool #9:  cross_check       ← cycle 2, FAIL
Tool #10: draft             ← cap hit, proceeded anyway
Tool #11: sense_check       ← PASS
Tool #12: FinalBrief        ← structured output produced
```

The orchestrator stopped at exactly 2 cross_check cycles and
proceeded to Phase 2 with the latest synthesis. From the
streamed narration:

> *"I've now reached my retry cap for cross_check (2 cycles
> maximum). The second cross_check has failed, so per workflow
> rules, I must proceed to Phase 2 with the best synthesis
> available. I'll now draft the four-section briefing."*

**What we did**: Nothing. Smoke run validated the design.

**Implication**: Three design decisions validated by this run:

1. **Retry-cap enforcement works in prose.** The model counts
   tool-call cycles from its own conversation history and stops
   at the named limit.
2. **Cap-fallback behaviour works.** *"Proceed to Phase 2 anyway
   with the best synthesis available"* — the model followed this
   instruction precisely, didn't get stuck waiting for an audit
   that would never pass.
3. **Selective re-research works.** The orchestrator read
   `RE-RESEARCH TARGETS: news` from the cross_check output and
   re-ran only `research_news` in cycle 2, preserving the other
   research streams. Cost-conscious behaviour working as
   intended.

---

## 2026-05-11 — sense_check retry-cap enforcement works under failure (and the model reasons about the test)

**Observed**: Failure-path smoke test with a stubbed sense_check
that always returns `VERDICT: FAIL`. The orchestrator's
tool-call trace:

```
Tool #1:  fetch_price
Tool #2:  research_news
Tool #3:  research_catalysts
Tool #4:  research_geo
Tool #5:  synthesise
Tool #6:  cross_check          ← real, PASS
Tool #7:  draft
Tool #8:  sense_check          ← cycle 1, stubbed FAIL
Tool #9:  revise               ← acted on stub's generic notes
Tool #10: sense_check          ← cycle 2, stubbed FAIL
Tool #11: FinalBrief           ← cap hit, proceeded
```

The orchestrator stopped at exactly 2 sense_check cycles. revise
was called between the two failed audits, so the orchestrator
attempted the fix before giving up — didn't just count to 2 and
stop.

**The more interesting observation**: the orchestrator
*recognised the stub for what it was*. From its narration:

> *"The sense_check is returning a test stub that always fails
> (as noted in the output). This is a cap-testing scenario. I've
> now run two sense_check cycles (initial draft failed, revision
> failed), which is the maximum allowed. Per the rules, I must
> accept the current draft and proceed to final output."*

The stub's response contains the phrase *"Test stub: this
auditor always returns FAIL to exercise the orchestrator's
retry-cap logic"* — the model read this, inferred the test
scenario, and explicitly named what was happening before
proceeding correctly. Reasoning about the situation, not just
mechanical execution.

**What we did**: Nothing. Smoke run validated the design.

**Implication**: Both retry loops use the same prompt-only
mechanism and both work under genuine failure conditions. The
orchestrator's behaviour generalises across the two loops; we
didn't just get lucky on cross_check.

Also: revise applied generic stub notes successfully. The stub's
REVISION NOTES were deliberately vague ("Tighten the news
section's opening to lead more directly with the synthesis's
identified dominant narrative...") because the stub doesn't see
the draft. revise produced a real change against this guidance.
Useful to know that revise can act on general feedback as well
as on specific quoted-text feedback.

---

## 2026-05-11 — Both retry loops validated; text-native bet comprehensively closed

**Observed**: After the two failure-path smoke tests
(cross_check stub, sense_check stub), both of the orchestrator's
retry loops are independently validated:

| Retry loop | Mechanism | Cap held? | Fallback worked? |
|---|---|---|---|
| cross_check | prose-only, declarative prompt | ✅ yes (2 cycles) | ✅ proceeded with best synthesis |
| sense_check | prose-only, declarative prompt | ✅ yes (2 cycles) | ✅ proceeded with revised draft |

The text-native bet from STEP-03 — including its riskiest
component, prompt-only retry-cap enforcement — has now been
comprehensively validated. The hybrid fallback ("hybrid where
quality forces it") has never been needed at any layer of the
agent.

**What we did**: Nothing. This is the standing assessment.

**Implication**: The Phase 2 build is feature-complete and design-
complete. No outstanding open questions from STEP-03; no known
failure modes that need addressing. The orchestrator handles:

- Happy path (both audits pass) → 9 specialist calls
- cross_check failure → re-research, re-synthesise, retry cap,
  fall back to Phase 2
- sense_check failure → revise, retry cap, fall back to Phase 3

What's left for Phase 2 is documentation (STEP-07 retrospective,
PR notes, Phase 2 retrospective), not code.

---

## 2026-05-11 — All five STEP-03 open questions formally closed

After PR 5 (orchestrator + both failure-path tests), all of
STEP-03's named "things we'll be watching for" are answered:

| STEP-03 open question | PR | Result |
|---|---|---|
| CROSS-STREAM SIGNALS reliably produced | PR 3 | ✅ closed positive |
| VERDICT line interpreted correctly | PR 3, 4 | ✅ closed positive |
| revise stays distinct from draft | PR 4 | ✅ closed positive |
| Retry-cap enforcement from prose alone | PR 5 (cross_check) | ✅ closed positive |
| Retry-cap enforcement from prose alone | PR 5 (sense_check) | ✅ closed positive |
| Orchestrator manages input-string assembly | PR 5 | ✅ closed positive |

Six checks, six positive closures. The text-native design from
STEP-03 has held under every test. The orchestrator's prompt
length is a real cost (it's the longest prompt in the project),
but its enforcement is robust.

**What we did**: Updated the standing assessment.

**Implication**: Phase 2 has produced strong evidence that
agents-as-tools with declarative orchestrator prompts can encode
non-trivial workflow logic — including retry caps and selective
re-execution — without resorting to structured state or
programmatic safety nets. The orchestrator's prompt is the
specification; the model is the executor.

This is a meaningful result for the eventual Phase 1 vs Phase 2
comparison: Phase 1 encoded workflow as graph topology and state
plumbing; Phase 2 encoded it as prose. Both work. The interesting
question for the retrospective is what the tradeoffs are.
