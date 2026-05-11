## 2026-05-11 — draft, sense_check, revise: all tools-less, all clean openings

**Observed**: All three rendering-layer specialists opened cleanly
with their structural marker on the first character:

- draft: `PRICE SECTION` (no preamble)
- sense_check: `VERDICT: PASS` / `VERDICT: FAIL` (no preamble)
- revise: `PRICE SECTION` (no preamble)

Standing count after PR 4:

- Tool-equipped specialists: preamble 7/7
- Tools-less specialists: preamble 0/8 (synthesise, cross_check,
  draft, sense_check, revise across multiple runs)

15 runs across 8 specialists. The pattern is solid.

**What we did**: Nothing. Hypothesis robust.

**Implication**: The orchestrator's parser logic finalised:

- The four tool-equipped research specialists need leniency for
  leading preamble — skip lines until a structural marker.
- The remaining six specialists (synthesise, cross_check, draft,
  sense_check, revise, fetch_price-as-tool) can be parsed strictly
  from the first character.

This is a real architecture-level simplification compared to
treating all specialists uniformly. Worth carrying into the
orchestrator design.

---

## 2026-05-11 — sense_check pass-bias produces "PASS with notes" (as designed)

**Observed**: sense_check on a clean draft (PASS scenario) returned
`VERDICT: PASS` but also flagged a minor STRUCTURE issue —
suggesting that the Xi-Trump summit catalyst could be more
prominently positioned. The REVISION NOTES section was labelled
as "Optional tightening only" and offered a specific reordering
suggestion.

This is exactly the "pass with notes" calibration Phase 1 was
tuning for. The auditor:
- Used pass-bias correctly (didn't fail on a stylistic preference)
- Surfaced a real but minor consideration for downstream awareness
- Labelled the note explicitly as optional rather than required

**What we did**: Nothing. Working as designed.

**Implication**: The "would a competent reader notice this problem?"
framing from Phase 1 ports verbatim and produces the right
calibration in Phase 2. Pass-bias instructions are doing the work
they need to do, both for cross_check (PR 3) and now for sense_check.

The orchestrator should treat PASS verdicts as proceed-to-deliver
regardless of optional notes. If we ever want the optional notes
to feed forward (e.g., to revise as polish), that's a future
enhancement — for now, PASS = ship.

---

## 2026-05-11 — sense_check detected faithfulness violation with specific localisation

**Observed**: sense_check on a corrupted draft (FAIL scenario)
returned `VERDICT: FAIL` and:

- Quoted the exact injected sentence
- Identified which sections of the brief AND of the synthesis it
  contradicted
- Wrote actionable REVISION NOTES specifying which sentence to
  delete and what the section should open with instead

This is the second auditor following the same fabrication-injection
pattern as cross_check (PR 3) and detecting at the same quality
level — specific quote, specific location, actionable fix.

**What we did**: Nothing. Validation of the auditor pattern.

**Implication**: The fabrication-injection test pattern works
equally well for both auditors. The pattern — "inject one specific
known-bad thing, verify the auditor catches it" — is now a
reusable template for any future auditor we might add.

The REVISION NOTES output is genuinely actionable. revise was
able to use it directly (see next entry).

---

## 2026-05-11 — revise stays targeted (side-by-side comparison confirms)

**Observed**: With the updated smoke_revise.py that prints both
the original draft and the revised brief plus per-section
similarity ratios, the answer to "did revise stay targeted?" is
definitively yes:

```
PRICE SECTION          100.00%   verbatim
NEWS SECTION           100.00%   verbatim
CATALYSTS SECTION       93.43%   trivial changes
GEOPOLITICS SECTION    100.00%   verbatim
```

The NEWS SECTION result is initially counterintuitive — sense_check
flagged it as the section needing the biggest fix. But it's the
right answer: sense_check asked revise to *delete* the injected
opening sentence and *open with* a specific sentence ("Trump's
rejection of Iran peace talks is the day's consequential story...").
That sentence was *already* the opening of the original
(uncorrupted) draft. The corruption was a prepend; revise removed
exactly what was prepended. Net result: identical to original.

The CATALYSTS SECTION 93.43% reflects the secondary fix sense_check
asked for — rewording one sentence about frontrunning risk to be
sharper. One sentence changed in one section, exactly as instructed.

**What we did**: Nothing. Validation.

**Implication**: STEP-03's open question — *"If revise fires but
produces fresh drafts instead of targeted fixes, the prompt isn't
holding the distinction"* — answered. The prompt's bolded
*"targeted revision, not a rewrite"* instruction is sufficient.
Phase 1's lesson ports unchanged.

**Methodological note**: My previous interpretation of an earlier
smoke run (which suggested revise was drifting toward broader
rewriting) was based on comparing the revised brief against memory
of a different chain run's draft. That's not a valid comparison —
different chain runs produce different drafts, all reasonable.
The corrected smoke test compares within a single chain run and
gives the definitive answer.

Lesson: when assessing "did this specialist preserve unchanged
content," always compare against the *same run's* upstream output,
never against memory of previous runs.

---

## 2026-05-11 — smoke test design: in-run side-by-side comparison required for any "did it preserve content?" question

**Observed**: The first version of smoke_revise.py couldn't answer
"did revise stay targeted?" without manual comparison against
memory or a prior run. The updated version prints both the
original draft and the revised brief from the *same chain run*
plus per-section similarity ratios via difflib.SequenceMatcher.

This makes the targeted-revision verdict mechanical: each
section gets a similarity ratio in [0, 1] with a categorical
verdict (`verbatim` ≥ 0.98, `trivial changes` ≥ 0.85, `partial
rewrite` ≥ 0.50, `substantial rewrite` < 0.50). The thresholds
are eyeball-calibrated heuristics but worked first try.

**What we did**: Updated the smoke test. Re-ran. Got definitive
answer.

**Implication**: This pattern — in-run side-by-side comparison
with similarity ratios — is the right shape for any future
smoke test that asks "did the specialist preserve content it
wasn't asked to change?" Future revise-shaped specialists (if
any) should use the same pattern. Worth noting in the eventual
STEP retrospective as a reusable smoke-test technique.

The difflib stdlib is sufficient — no need for external diff
libraries. SequenceMatcher.ratio() is fast enough for full-text
section comparisons at our scale.
