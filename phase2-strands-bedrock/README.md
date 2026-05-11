# Phase 2 — Strands Agents on Bedrock AgentCore Runtime

The second implementation of the Commodity Briefing Agent. Built
with Strands' agents-as-tools pattern, calling Claude via Amazon
Bedrock.

This is one of three implementations — see the
[project README](../README.md) for the broader context, and the
[Phase 2 retrospective](../docs/retrospectives/phase-2-retrospective.md)
for a side-by-side comparison with Phase 1.

## Architecture summary

1 orchestrator + 8 specialists + 1 plain tool. The orchestrator
plans the workflow via a declarative system prompt; specialists
are wrapped as `@tool`-equivalent agents in its `tools=[]` list.

```
Orchestrator
├── fetch_price (plain tool)
├── research_news        ← Tavily-bound
├── research_catalysts   ← Tavily-bound
├── research_geo         ← Tavily-bound
├── synthesise           ← tools-less
├── cross_check          ← auditor, returns VERDICT: PASS / FAIL
├── draft                ← tools-less
├── sense_check          ← auditor, returns VERDICT: PASS / FAIL
└── revise               ← tools-less, targeted re-renderer
```

The orchestrator's workflow has three phases:

1. **Research & synthesis** — gather four research streams,
   synthesise, audit with cross_check. Re-research if FAIL
   (max 2 cycles, then proceed).
2. **Rendering** — draft, audit with sense_check. Revise if FAIL
   (max 2 cycles, then proceed).
3. **Final output** — orchestrator produces `FinalBrief` (subject,
   html_body, plain_text_body) as structured output.

Full design discussion: [`docs/tutorials/phase-2/03-design.md`](../docs/tutorials/phase-2/03-design.md).

## Setup

```bash
cd phase2-strands-bedrock
uv sync
```

Set up the environment file (not checked in):

```bash
cp env-example.txt .env
# Add TAVILY_API_KEY=...
# AWS credentials come from SSO profile (see below)
```

AWS access uses SSO. The agent expects credentials available via
the default credential chain — easiest is to set `AWS_PROFILE`
and run `aws sso login` before invoking. The `eu.anthropic.claude-haiku-4-5`
cross-region inference profile is used; ensure your account has
access in the configured region (default `eu-west-1`).

## Running the agent end-to-end

```bash
uv run python -m briefing_agent.smoke_orchestrator
```

Produces an end-to-end commodity briefing for today. The
orchestrator narrates each step ("Now I'll synthesise...", "Cross_check
passed; moving to draft...") and emits a `FinalBrief` at the end.

Cost is ~10–15 cents per happy-path run.

## Smoke tests

No pytest suite (yet). Validation is via manual smoke runners:

| Runner | Purpose |
|---|---|
| `smoke_fetch_price` | Plain tool sanity |
| `smoke_research_news` | News research specialist |
| `smoke_research_catalysts` | Catalysts research specialist |
| `smoke_research_geo` | Geopolitics research specialist |
| `smoke_synthesise` | Live chain: research × 4 → synthesise |
| `smoke_cross_check` | Live chain + cross_check pass + fail scenarios |
| `smoke_draft` | Live chain → draft |
| `smoke_sense_check` | Live chain + sense_check pass + fail scenarios |
| `smoke_revise` | Live chain + chained revise with diff comparison |
| `smoke_orchestrator` | Full end-to-end happy path |
| `smoke_orchestrator_failure` | Stubbed cross_check, retry-cap test |
| `smoke_orchestrator_failure_sense` | Stubbed sense_check, retry-cap test |

Run any of them with `uv run python -m briefing_agent.<runner>`.

## Project layout

```
phase2-strands-bedrock/
├── pyproject.toml
├── uv.lock
├── env-example.txt
├── verify_setup.py             # one-shot AWS/Bedrock/Tavily auth check
├── docs/
│   └── observations.md         # build-period text-native findings
└── src/
    └── briefing_agent/
        ├── __init__.py
        ├── final_brief.py      # FinalBrief Pydantic model
        ├── orchestrator.py     # orchestrator agent factory
        ├── tools.py            # fetch_price + tavily_search re-export
        ├── specialists/
        │   ├── research_news.py
        │   ├── research_catalysts.py
        │   ├── research_geo.py
        │   ├── synthesise.py
        │   ├── cross_check.py
        │   ├── draft.py
        │   ├── sense_check.py
        │   └── revise.py
        ├── prompts/
        │   ├── __init__.py     # load_prompt helper
        │   ├── orchestrator.md
        │   ├── news.md
        │   ├── catalysts.md
        │   ├── geopolitics.md
        │   ├── synthesise.md
        │   ├── cross_check.md
        │   ├── draft.md
        │   ├── sense_check.md
        │   └── revise.md
        └── smoke_*.py          # 12 manual smoke runners
```

## Tutorial steps

The full coaching-mode walkthrough is in
[`../docs/tutorials/phase-2/`](../docs/tutorials/phase-2/),
STEP-01 through STEP-07.
