## 2026-05-11 — Phase 3 environment verified end-to-end

**Observed**: `verify_setup.py` exercised the full ADK + Vertex +
Gemini 2.5 Flash + `google_search` chain on the first run.
118 packages installed, environment loaded cleanly, agent
invoked, search-grounded response returned, FinalBrief-style
output produced.

Installed versions captured:
- `google-adk==1.33.0`
- `google-genai==1.75.0`

**What we did**: Pinned both versions in `pyproject.toml` after
the verify run passed (matching Phase 2 retrospective's
"validate then pin" rule). Ran `uv lock` — clean 6ms resolution,
no version conflicts.

**Implication**: Phase 3's environment is ready for design work
in STEP-03. The framework choice (ADK), the model (Gemini 2.5
Flash), and the search tool (`google_search`) are all functional.

---

## 2026-05-11 — Quota project warning fix required first run

**Observed**: The first verify run emitted a UserWarning from
`google.auth._default`:

> *"Your application has authenticated using end user credentials
> from Google Cloud SDK without a quota project. You might
> receive a 'quota exceeded' or 'API not enabled' error."*

This is ADC's default behaviour when authenticated via user
credentials without an explicit quota project set. API calls
worked anyway (the response came back fine), but for sustained
use the warning is real — Vertex calls weren't being billed to
the right project's quota pool.

**What we did**: One-time fix with
`gcloud auth application-default set-quota-project carty-470812`.
Re-ran verify, warning gone.

**Implication**: This is a setup gotcha that the official ADK
quickstart doesn't surface. Worth adding to STEP-02 as a
required step rather than a "fix if you see it" — running ADC
login alone isn't sufficient for clean Vertex auth, you also
need the quota project explicitly bound.

Updated to STEP-02 procedure: after `gcloud auth
application-default login`, immediately run
`gcloud auth application-default set-quota-project
$GOOGLE_CLOUD_PROJECT`.

---

## 2026-05-11 — Gemini 2.5 Flash response variance is real

**Observed**: Same query ("What is the current price of WTI
crude oil per barrel?"), two runs with different shapes:

**Run 1 (before quota fix):**
> *"As of May 11, 2026, the price of WTI crude oil is
> approximately $97.21 per barrel, marking a 1.88% increase
> from the previous day. Other sources indicated a price of
> $98.87 as of May 8, 2026, with futures trading around $97.16
> and a daily range between $96.63 and $100.35."*

**Run 2 (after quota fix):**
> *"As of May 11, 2026, the price of WTI crude oil is reported
> to be $97.21 USD per barrel."*

Same model, same query, same agent config. Two genuinely
different responses — one rich and multi-source-reconciled,
one terse and single-figure.

**What we did**: Nothing yet. Logged.

**Implication**: This is normal LLM non-determinism, not a bug.
Phase 2's Haiku 4.5 was similarly variable. But it's an early
signal for Phase 3's design that:

1. Research specialists will need prompt-level discipline to
   reliably produce multi-source reconciled responses (the Run 1
   shape) rather than terse single-figure summaries (the Run 2
   shape). Phase 1 and 2's research prompts handled this; the
   lessons should port.
2. Validation needs to account for variance — single-shot smoke
   tests can produce different outputs each run. The
   fabrication-injection pattern from Phase 2 is more robust
   than "expect this exact string" assertions.

The Phase 2 retrospective said "prompt-level discipline is the
portable layer." This is a tiny early data point that the same
hypothesis holds for Gemini: the model's defaults are variable;
prompts shape it.

---

## 2026-05-11 — `google_search` quality is at least good enough to replace Tavily

**Observed**: The `google_search` tool returned current,
grounded, multi-source content on the first try. The Run 1
response above reconciled three sources (one with a specific
price, one with a different price from a different date, one
with futures trading range data) into a coherent summary.

**What we did**: Nothing. Validation.

**Implication**: STEP-01 flagged web search as an open question
— "is `google_search` quality good enough to replace Tavily?"
Initial answer is yes, the tool is competitive on this single
query.

We won't know how well it handles the more complex research
prompts (Phase 2's research_news, research_catalysts,
research_geo each had 4-5 specific item requests) until PR 1+
in Phase 3. But the basic mechanism is sound and the search
results are real, not stubbed.

---

## 2026-05-11 — ADK install footprint is larger than Strands

**Observed**: `uv sync` installed 118 packages for ADK +
google-genai + python-dotenv + pydantic. For comparison, Phase
2's Strands install was substantially smaller (didn't capture
the exact count at the time, but Strands is a leaner framework).

The footprint includes things like:
- OpenTelemetry libraries (ADK has built-in tracing support)
- FastAPI / Starlette (for the `adk web` UI we're not using)
- Click (for the `adk` CLI we're not using)
- A2A protocol libraries

**What we did**: Nothing. Logged for cost/dependency awareness.

**Implication**: ADK is more of a *platform* and less of a
*library* than Strands. It includes the dev UI, the API server,
the eval framework, and the OTel hookups in the base install.
For a small agent project, much of this is unused weight.

Two consequences for Phase 3:
- **Deploy footprint** (if we go to Agent Engine in STEP-03) will
  be larger than Phase 2's Bedrock equivalent.
- **Import time** for `verify_setup.py` is noticeably slower
  than Phase 2's Strands import. Not a problem for a one-shot
  verify; could become noticeable if we run many smoke tests in
  sequence.

Phase 1 vs Phase 2 vs Phase 3 install size is now a meaningful
data point for the eventual three-phase retrospective.

## 2026-05-12 — Prompt-port-verbatim hypothesis holds for Gemini Flash

**Observed**: First Phase 3 specialist (`research_news`) used the
`news.md` prompt unchanged from Phase 2. Smoke output was
format-compliant on first attempt:

- Five items, labelled `ITEM 1` through `ITEM 5`
- All six required fields per item (Headline, Source, URL, Why it
  matters, Direction, Timeframe)
- `Direction` values correctly one of three allowed strings;
  `Timeframe` correctly one of two
- No preamble or closing commentary (both forbidden by the prompt)

**What we did**: Nothing. The hypothesis held, the prompt didn't
need adjustment.

**Implication**: This is the first concrete validation of the Phase
2 retrospective's claim that "prompt-level discipline is the portable
layer." A prompt written for Claude Haiku 4.5 produced equivalent
format compliance on Gemini 2.5 Flash without any modification.

This makes PRs 2-5 substantially less risky. The remaining seven
specialists (catalysts, geopolitics, synthesise, cross_check, draft,
sense_check, revise) can all be expected to port verbatim. If any
*doesn't* port cleanly, that's the surprise worth investigating.

---

## 2026-05-12 — google_search returns Vertex grounding redirect URLs, not direct source URLs

**Observed**: Every URL in `research_news`'s output uses the form:

```
https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEY...
```

These are click-tracked redirects, not direct publisher URLs.
Comparison with Phase 2 Tavily output (which returned URLs like
`https://reuters.com/business/...`) shows this is a meaningful
difference in citation shape.

Additionally, when an ITEM cites multiple sources, the URL field
becomes a comma-separated list of redirect URLs. ITEM 1 in the
smoke run cited six sources and produced six concatenated URLs.

The `Source` field still carries the human-readable publisher names
(Reuters, EIA, OPEC, etc.), so attribution works for a reader.

**What we did**: Nothing structural — captured in STEP-04 as a
finding. The pattern is documented behaviour of Vertex AI Search
Grounding (Google routes all grounding citations through the
redirect for usage tracking).

**Implication**: Three things to watch in subsequent PRs:

1. **Catalysts and geopolitics specialists will show the same
   pattern.** Confirmed expected; no workaround needed for research
   itself.
2. **The synthesis layer (PR 3) reads research output verbatim.**
   The synthesise prompt should be checked for any assumption that
   URLs are direct (probably none — synthesis cares about facts,
   not link targets).
3. **The draft layer (PR 4) needs a decision: should URLs surface
   to the briefing reader, or should we strip them and rely on
   the `Source` field?** Phase 2 included URLs; Phase 3 may want
   to suppress them given they're opaque redirects.

This is a real cross-phase difference. Worth a section in the
Phase 3 retrospective when we get there: "the `google_search`
grounding model is not a drop-in replacement for direct search
APIs in citation-quality terms, even though content quality is
comparable."

---

## 2026-05-12 — Runner helper pattern proven, will be reused

**Observed**: `briefing_agent.runner.run_specialist(agent, query)`
extracted the ADK `Runner` + `InMemorySessionService` + event-loop
walking into ~30 lines of helper code. The smoke test for
`research_news` became a 6-line async main function as a result.

**What we did**: Nothing more. Will reuse for every subsequent
specialist smoke test.

**Implication**: ADK's invocation surface is verbose (Strands was
one line: `agent(query)`). The helper amortises that boilerplate.
For PR 2 we'll have `smoke_research_catalysts` and
`smoke_research_geo`, each one-line against `run_specialist`.

The orchestrator (PR 5) will NOT use this helper — it has its own
event-handling logic with the `event.actions.escalate = False`
suppression workaround. This helper is development-only.

---

## 2026-05-12 — yfinance + dataclass + asdict pattern ports cleanly

**Observed**: `fetch_price` smoke ran first attempt. All 12
`PriceSnapshot` fields populated, numbers in plausible ranges:

- CL=F at $98.89 on 2026-05-12 (note: STEP-02 verify showed ~$97
  the day before; ~2% daily move is normal)
- Daily change +0.84%, intraday range 1.30%
- 5-day avg $96.45, 20-day avg $96.80 (close to spot, suggests
  recent stable trading)
- 52-week range $54.98 – $119.48 (wide, captures the 2025-2026
  geopolitical-tension-driven volatility)

**What we did**: Nothing. yfinance worked, dataclass serialised,
no surprises.

**Implication**: Phase 1 → Phase 2 → Phase 3 `fetch_price` is now
proven across all three phases. The PriceSnapshot data shape is
the stable contract; only the wrapping (class, @tool, plain
function) changes per phase.

## 2026-05-12 — Prompt-port-verbatim hypothesis holds for catalysts and geopolitics

**Observed**: Both `catalysts.md` and `geopolitics.md` ported
verbatim from Phase 2 and produced format-compliant output on
first run:

- Catalysts: 7 EVENT blocks, all six required fields, correct
  Importance values (high/medium/low)
- Geopolitics: 5 THEME blocks, all five required fields, correct
  Impact direction / Timeframe / Confidence values, distinct
  themes (no overlap)

**What we did**: Nothing — prompts didn't need adjustment.

**Implication**: Three out of three research-layer prompts have
now ported verbatim. The hypothesis is solidly established for
research specialists. PRs 3 and 4 (synthesise, cross_check, draft,
sense_check, revise) should be assumed to follow the same pattern;
any specialist whose prompt DOESN'T port verbatim is the surprise
worth investigating.

---

## 2026-05-12 — Catalysts prompt has no item cap; Gemini returned 7 events

**Observed**: The catalysts prompt (unlike news.md's "Aim for
3-5 items") has no explicit cap on event count. Gemini returned
7 events. The first 4-5 were directly oil-relevant (CPI, API
inventory, two oil major earnings); events 5-7 were tangential
macro (two Fed speakers, BoJ summary).

The Phase 2 prompt had the same lack of cap and presumably the
same behaviour — but Phase 2's catalysts smoke logs aren't here
to compare.

**What we did**: Nothing. Logged.

**Implication**: Considering adding a soft cap to catalysts.md
("Aim for 3-6 events") in a future revision. Deferred because:
1. The downstream synthesis layer (PR 3) may handle long event
   lists fine
2. Changing the prompt mid-port-validation muddies the cross-
   phase comparison
3. Other prompt revisions may emerge from PRs 3-5; better to
   batch any prompt tuning at the end

Worth revisiting after PR 5 once we see how the orchestrator
consumes catalysts output.

---

## 2026-05-12 — ParallelAgent genuinely parallelises; 3 streams in single-stream time

**Observed**: `smoke_research_parallel` completed in 18.2 seconds
running three sub-agents concurrently. For comparison, each
individual specialist smoke ran in roughly 20-40 seconds
standalone.

The three sub-agents are: news (with google_search), catalysts
(with google_search), geo (with google_search). All three doing
real search-grounded research. Total wall-clock under 20 seconds
for the combined research stage.

**What we did**: Nothing — validation. This was the most important
STEP-03 architectural assumption to verify.

**Implication**: The "parallel research" stage is essentially free
on latency vs running one specialist. The cost is purely token
spend (three concurrent specialists = three sets of search +
synthesis tokens). For the eventual orchestrator (PR 5), parallel
research is the right pattern — no reason to fall back to
sequential research.

This is a meaningful Phase 3 win vs Phase 2. Phase 2's
orchestrator ran the three research specialists sequentially
through its tool-call loop. Phase 3 can do them all at once
because ADK has a first-class primitive for it.

---

## 2026-05-12 — Workflow agent event stream is coarse; intermediate events stay inside sub-agent branches

**Observed**: `smoke_research_parallel` produced exactly 3 events
from the top-level Runner's perspective — one per sub-agent. No
intermediate tool-call events, no sub-agent reasoning events.
Just three "specialist finished" notifications.

Each sub-agent presumably emitted many internal events
(tool-call requests, tool responses, intermediate model
generations) but those stay inside the sub-agent's
InvocationContext branch and don't propagate up to the
ParallelAgent's external event stream.

**What we did**: Nothing — observed and logged.

**Implication**: Two consequences:

1. **Orchestrator design (PR 5) gets simpler.** The orchestrator
   doesn't need to handle interleaved events from three
   concurrent specialists — it just waits for the ParallelAgent
   to finish, then reads three state keys.

2. **Observability is coarser than Phase 2's.** In Phase 2, the
   orchestrator saw every tool call from every specialist
   because everything ran sequentially through one agent's
   event stream. In Phase 3, per-specialist visibility requires
   either:
   - Inspecting per-branch session state (which is what we did
     in the smoke)
   - Wiring up ADK callbacks (`before_model_callback`,
     `after_tool_callback`) on each specialist for finer-grained
     tracing
   - Using Cloud Trace (deferred per STEP-03)

Worth a section in the Phase 3 retrospective: ADK's workflow
agents trade observability for execution efficiency. For
production, you'd want callback-based tracing or Cloud Trace.

---

## 2026-05-12 — Generic parallel user message produced terser per-stream output

**Observed**: Comparing standalone smoke output vs parallel-smoke
output for the same specialists:

- News: 5 items standalone, 4 items parallel
- Geo: 5 themes standalone, 4 themes parallel

The user message differed:
- Standalone (news): "Find the most important oil-related news
  from the last 24 hours for today's briefing."
- Parallel: "Conduct full research across news, catalysts, and
  geopolitics."

The system prompt (which says what each specialist produces) was
identical in both cases. The user message in the parallel case
was generic — and each specialist produced slightly less.

**What we did**: Logged. Will revisit in PR 5 orchestrator design.

**Implication**: For PR 5 orchestrator, the user message that
seeds the parallel stage can't reasonably be tailored per
specialist (ParallelAgent forwards one message to all sub-agents).
Three response options:

1. **Strengthen the prompts** so the system prompt alone drives
   output regardless of user-message generality. Lean toward
   this — matches the "editorial discipline lives in prompts"
   principle from Phase 2's retrospective.

2. **Sequential invocation** of each specialist with tailored
   user messages. Defeats the latency win — back to 3× time.

3. **Pre-stage prep** writes per-specialist context to session
   state. Specialists read from state. More plumbing, but
   preserves tailored context.

Recommendation: try (1) first in PR 5. If output quality drops
below standalone baseline, fall back to (3).

---

## 2026-05-12 — `session_service.get_session(...).state` pattern works cleanly for state inspection

**Observed**: After a workflow run, fetching the completed
session via the session service and reading `state[output_key]`
returned the populated output for each sub-agent. Three keys
populated, none missing:

```python
completed = await session_service.get_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=session.id,
)
news = completed.state.get("news_research")
catalysts = completed.state.get("catalysts_research")
geo = completed.state.get("geo_research")
```

**What we did**: Pattern used in the parallel smoke; works
reliably.

**Implication**: This is the canonical way to introspect ADK
workflow output. PR 3 and PR 4 smoke tests can reuse this
pattern when testing LoopAgent stages. The orchestrator (PR 5)
will access state via `ctx.session.state[key]` from inside the
`_run_async_impl` method — same data, different access path.
