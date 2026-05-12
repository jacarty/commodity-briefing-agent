# STEP-04 — First specialist: news research + price fetch

The first code lands. Ports the prompts/loader pattern from Phase 2,
adds `fetch_price` (un-decorated this time), builds the first ADK
`LlmAgent`, and validates the prompt-port-verbatim hypothesis for
Gemini 2.5 Flash.

Two of STEP-03's six open questions get answered here:
- **Does the prompt-port-verbatim hypothesis hold for Gemini?** Yes.
- **Does `google_search` produce research output as rich as Tavily?**
  Mostly yes — content quality matches, but citation URL shape is
  different (see "The grounding URL finding" below).

## What's in this PR

Six new source files and one pyproject change:

| File | Role |
|---|---|
| `pyproject.toml` | Add `yfinance` (for `fetch_price`) |
| `src/briefing_agent/prompts/__init__.py` | Prompt loader, ports verbatim from Phase 2 |
| `src/briefing_agent/prompts/news.md` | News research prompt, ports verbatim from Phase 2 |
| `src/briefing_agent/tools.py` | `fetch_price` and `PriceSnapshot` (no decorator) |
| `src/briefing_agent/runner.py` | Async helper to invoke a single specialist |
| `src/briefing_agent/specialists/__init__.py` | Empty package marker |
| `src/briefing_agent/specialists/research_news.py` | First ADK `LlmAgent` factory |
| `src/briefing_agent/smoke_fetch_price.py` | Smoke test for `fetch_price` |
| `src/briefing_agent/smoke_research_news.py` | Smoke test for `research_news` |

## What ports verbatim from Phase 2

**The prompt loader (`prompts/__init__.py`).** Phase 1 → Phase 2 → Phase
3 use the same loader. Markdown files in a directory, loaded by name,
optional `str.format()` substitution. Three lines of real code.

**The news prompt (`prompts/news.md`).** Character-for-character
identical to Phase 2's. The hypothesis from Phase 2's retrospective
("editorial discipline lives in prompts, prompts are framework-
portable") got its first real test here and held.

**`PriceSnapshot` (in `tools.py`).** Same dataclass, same fields, same
units. Phase 1 used a class with `.fetch`. Phase 2 used `@tool`. Phase
3 uses a plain function — the orchestrator calls it directly per
STEP-03 design.

## What changes vs Phase 2

**`fetch_price` has no decorator.** Phase 2 wrapped it with Strands'
`@tool` because specialists used it as a tool. Phase 3's design has
the custom orchestrator call `fetch_price` directly (no LLM
involved), so the function is just a function. If a future change
needs to expose it to an agent, wrap it with
`google.adk.tools.FunctionTool` at that point.

**The specialist factory builds an ADK `LlmAgent`.** Different class,
different parameter names, mostly the same configuration:

| Phase 2 (Strands `Agent`) | Phase 3 (ADK `LlmAgent`) |
|---|---|
| `name="research_news"` | `name="research_news"` |
| `description=...` | `description=...` |
| `system_prompt=load_prompt("news")` | `instruction=load_prompt("news")` |
| `model=BedrockModel(...)` | `model="gemini-2.5-flash"` |
| `tools=[tavily_search]` | `tools=[google_search]` |
| `callback_handler=None` | — (not needed; ADK doesn't stream by default) |
| — | `output_key="news_research"` |

The two genuinely new bits:

- **Model passing.** ADK accepts a model ID string directly; the
  framework resolves it against the Vertex backend (configured in
  STEP-02 via `GOOGLE_GENAI_USE_VERTEXAI=True`). No explicit model
  object construction.
- **`output_key`.** When this agent runs as part of a workflow, its
  final response is automatically written to
  `session.state["news_research"]`. Phase 1 had this via explicit
  reducer functions in the graph; Phase 2 had it implicit in the
  orchestrator's prompt-building. Phase 3 has it native.

**The smoke test is async.** Phase 2's was synchronous because
Strands' `Agent.__call__` was sync. ADK's `Runner.run_async` is
async-first. Three mechanical points:

1. `load_dotenv()` runs BEFORE importing ADK — `google-genai`
   checks `GOOGLE_GENAI_USE_VERTEXAI` at import time.
2. `asyncio.run(main())` at the entry point.
3. The runner helper (`runner.py`) hides the
   `Runner` + `Session` + event-loop boilerplate.

## The runner helper

ADK's canonical invocation pattern is:

```python
session_service = InMemorySessionService()
session = await session_service.create_session(app_name=..., user_id=...)
runner = Runner(app_name=..., agent=agent, session_service=session_service)

async for event in runner.run_async(user_id=..., session_id=..., new_message=...):
    if event.is_final_response() and event.content and event.content.parts:
        final_response = event.content.parts[0].text
```

That's ~8 lines per smoke test. We'll have eight specialists by PR 5,
so the boilerplate adds up. `briefing_agent.runner.run_specialist`
wraps it. Each smoke test is a one-liner against the helper.

## What ran

Both smoke tests passed on first attempt.

**`smoke_fetch_price`**:
- Symbol `CL=F` (WTI crude futures)
- Last close $98.89 on 2026-05-12
- Daily change +0.84%
- Intraday range 1.30%
- 5-day avg $96.45 / 20-day avg $96.80
- 52-week range $54.98 – $119.48
- All 12 `PriceSnapshot` fields present and well-typed

Deterministic, as expected. yfinance worked first try.

**`smoke_research_news`**:
- Output started with `ITEM 1` and ran through `ITEM 5` — exactly the
  prompt's requested format
- Five substantive items: US-Iran tensions, SPR release, Strait of
  Hormuz disruption, OPEC+ June production decision, US crude
  inventory drawdown
- All six required fields per item (Headline, Source, URL, Why it
  matters, Direction, Timeframe)
- `Direction` values correctly one of `supports_trend / reverses_trend
  / neutral`; `Timeframe` correctly one of `short_term / structural`
- No preamble, no closing commentary (the prompt forbade both, and
  Gemini obeyed)

**Prompt-port-verbatim hypothesis held.** Gemini followed the
Phase 2 prompt without modification.

## The grounding URL finding

The one real surprise: **`google_search` URLs are Vertex AI
grounding-redirect URLs, not direct publisher URLs.** Every URL in
the smoke output looks like:

```
https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEY...
```

This is a click-tracked redirect that resolves to the original
source when followed. The actual source name is preserved in the
`Source` field (e.g. "Reuters", "The Economic Times", "EIA"), but
the URL field itself doesn't carry that information.

Two consequences:

1. **Citation quality is degraded vs Phase 2.** Tavily returned
   direct publisher URLs (`https://reuters.com/...`); google_search
   returns opaque redirects. A briefing reader can't see the source
   in the URL — only after clicking through. The `Source` field
   carries the human-readable attribution.
2. **Multi-source items concatenate URLs as comma-separated
   strings.** When an ITEM cites multiple sources (ITEM 1 cited
   six), the URL field becomes a comma-separated list of redirect
   URLs. The prompt doesn't anticipate this format — the prompt
   says "url" (singular).

This is a documented behaviour of Vertex AI's Search Grounding, not
a Gemini quirk. The redirect mechanism allows Google to track
citation usage for grounding quality measurement.

**For the briefing pipeline:** the `Source` field carries the
publisher names cleanly, so attribution still works in the final
brief. The `URL` field is a click-through link, not a human-readable
source. We may need to adjust the prompt later to handle the
multi-URL case (either "first URL only" or "list URLs explicitly").
Deferring to PR 2 or 3 when we see whether catalysts and geo
research show the same pattern.

## Findings to carry forward

| Finding | Implication for next PRs |
|---|---|
| Prompt-port-verbatim works for Gemini | Carry catalysts, geopolitics, synthesise, draft, audit prompts verbatim in PRs 2-5 |
| google_search content quality is competitive with Tavily | No need to fall back to Tavily |
| URL field carries Vertex redirects, not direct URLs | When we get to draft/render in PR 4, decide whether to surface URLs to the reader or rely on Source attribution |
| Multi-source items produce concatenated URL strings | May need to refine news.md or handle in synthesis |
| `output_key` auto-writes to `session.state` | Pattern works; use for all specialists |
| Runner helper makes smoke tests one-line | Reuse for all future specialist smokes |

## Open questions still ahead

After PR 1 closes, four of STEP-03's six open questions remain:

- `exit_loop` reliability → PR 3
- `event.actions.escalate = False` suppression → PR 5
- Gemini's PASS-with-notes calibration → PR 3
- `output_schema=FinalBrief` reliability → PR 5

## What's NOT in this PR

- `research_catalysts` and `research_geo` — PR 2
- `ParallelAgent` wrapping the three research specialists — PR 2
- The custom orchestrator — PR 5
- The retry loops — PR 3 and 4
- The FinalBrief output schema — PR 5
- Agent Engine deployment — PR 6

Strict scope discipline. PR 1 is the foundational PR — one specialist,
one tool, one smoke test pattern. Everything we learned here informs
how the rest get built.

## Reproducibility

```bash
cd phase3-vertex-gemini
uv sync
uv run python -m briefing_agent.smoke_fetch_price
uv run python -m briefing_agent.smoke_research_news
```

Outputs vary run-to-run (LLM non-determinism — STEP-02 already noted
this). The format compliance and the grounding URL shape are stable.
