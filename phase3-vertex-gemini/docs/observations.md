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
