# Reflections — when this pattern earns its keep

A note to future me. The commodity briefing agent works, but
"works" isn't the same as "was the right shape for the job."
Honest reading: for a daily personal oil briefing, this is
overkill. A single Claude call with a good prompt and four
research queries would have produced 80% of the same brief,
in maybe 30 seconds, for maybe a tenth of the cost.

So what *is* the pattern good for? Four design choices got made
during this build. Each one is worth keeping when its specific
problem shows up, and worth dropping when it doesn't.

## Design choice 1 — Parallel research

**What it is.** Three or four independent research streams
fanning out concurrently, results merged for synthesis.

**When it earns its keep.** The inputs are genuinely
independent (price, news, geopolitics — yes; "first reason about
X, then about Y based on X" — no), and you have a latency budget
where 3x sequential wouldn't fit but the model gives you a
parallel primitive that does.

**When it's overkill.** Single-source data. Sequential
reasoning where each step depends on the previous one's output.
A tight latency budget where audit loops would blow it anyway.

**Honest read on this project.** Parallel research was a real
win — ~18s vs ~20-40s sequential in Phase 3. But the briefing
agent runs once a day on a cron, so the latency saving is
cosmetic. The architectural lesson held; the operational benefit
didn't matter.

## Design choice 2 — Two-stage audit (cross-check + sense-check)

**What it is.** One auditor on the analytical content
(synthesise → cross-check), a different auditor on the rendered
prose (draft → sense-check). Each auditor returns PASS/FAIL and
triggers targeted revision on FAIL, bounded by retry cap.

**When it earns its keep.** This is the most expensive pattern
in the project, and it's the one with the narrowest justification.
The audit loops are worth the cost when:

- The output is consumed by someone who can't easily verify it
  themselves — a compliance summary for a non-lawyer, a medical
  history summary for a non-clinician, a financial brief for a
  client who isn't a trader
- The output's failure mode is *plausible-but-wrong* rather than
  *obviously-wrong* — fabricated numbers, missing context,
  weasel language that hides uncertainty
- The output drives an action that's costly to reverse — a memo
  that becomes a decision input, a customer reply, a forwarded
  brief that gets quoted back later
- You're building reader trust at scale and one bad output costs
  you a hundred good ones

**When it's overkill.** The reader can verify the output in
seconds (I would spot a wrong oil price). One-shot internal
scratch work. Outputs that get reviewed by a human before they
go anywhere consequential. Any chatbot turn — the audit cost
dwarfs the value.

**Honest read on this project.** Overkill. I'm the reader, I'm
also someone who would notice a wrong WTI close. The pattern
proved out and the prompts are reusable, but I would not put
audit loops in a v1 of a personal briefing tool again. I would
add them when a second person started reading the output, not
before.

## Design choice 3 — Prompt-as-orchestrator (Phase 2 pattern)

**What it is.** The orchestrator is a system prompt that
declares the workflow as a goal + constraints, not Python code
that imperatively wires nodes. The model decides what to call
next from its conversation history.

**When it earns its keep.** The workflow evolves often, and you'd
rather change a markdown file than redeploy a service. The
control flow is fuzzy enough that the model's routing decisions
are at least as good as `if/else`. You want non-engineers to be
able to tune the workflow.

**When it's overkill.** The control flow is well-defined and
won't change weekly. You need deterministic execution traces for
debugging or compliance. The retry/failure logic is too
specific to express in prose.

**Honest read on this project.** Phase 2's prompt-orchestrator
worked, but Phase 3's custom `BaseAgent` orchestrator was easier
to reason about under failure. Both are viable. The right answer
depends on whether the workflow is changing or settled.

## Design choice 4 — Bounded retry with safety-valve

**What it is.** Audit loops have explicit iteration caps (max 2)
with a forced-exit path on the cap. No way to spin forever.

**When it earns its keep.** This is the cheapest of the four
patterns and the most universally applicable. Any time an agent
can loop, a bounded retry is the answer. The cost of forgetting
this once is a billing alert and a stuck job.

**When it's overkill.** Never. Bounded retries are baseline
hygiene for anything with conditional loops.

**Honest read on this project.** Auditors in both Phase 2 and
Phase 3 hit iteration 2 on real-pipeline inputs about half the
time. The bound did real work. Keep it.

## So when *would* I build this whole shape?

A pattern that combines all four — parallel inputs, audit loops,
prompt orchestration, bounded retries — earns its full cost when
you can answer yes to most of:

- Multiple independent data sources, not a single pipeline
- Output consumed by a non-expert reader (or sent externally)
- Failure mode is plausible-but-wrong, not obviously-wrong
- Cost of being wrong > 10x cost of an extra few LLM calls
- Output is forwarded, archived, or quoted — not throwaway
- The workflow will be tuned by prompt edits, not code changes

Plausible real-world fits:

- **Compliance / policy briefs** — non-expert readers, plausible-
  but-wrong failure mode, forwarded onwards, audit trail matters
- **Customer-facing research replies** — trust at stake,
  high-volume so audit cost amortises
- **Investment / risk memos** — costly to reverse, sent to
  decision-makers, multiple independent inputs (financials,
  news, sentiment)
- **Medical / legal case summaries** — non-expert readers
  (clinician summarising for a patient, lawyer summarising for
  a client), classic plausible-but-wrong failure shape
- **Vendor / security assessments** — multiple sources (docs,
  posture data, CVE feeds), forwarded onwards, plausible-but-
  wrong is the worst kind of fail
- **Incident post-mortems** — multiple input streams (logs,
  timelines, chat), output consumed by leadership, accuracy
  matters

Plausible *poor* fits:

- A personal daily briefing (this project)
- Chatbots where each turn must be sub-second
- "Summarise this single document" — one call, one output,
  done
- Internal scratch / exploratory work where the human is the
  reviewer in the same session

## The honest one-liner

This pattern is a **trust engine**, not a productivity tool.
You build it when the reader can't verify the output and the
cost of being wrong is high. For a daily personal briefing,
the trust problem is solved by the fact that I'm the reader.
For a brief that goes to someone else, the calculus inverts.

The skills are portable. The code is keepable. But the next
time I reach for this shape, the question to answer first is:
*"Who's reading this, and what does it cost them if I'm
wrong?"* If the answer is "me, and not much," do the simple
thing.
