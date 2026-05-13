# Phase 3 — Google ADK on Vertex AI Agent Engine

The third implementation of the Commodity Briefing Agent. Built
with Google's Agent Development Kit (ADK), using Gemini 2.5 Flash
as the model, and deployed to Vertex AI Agent Engine.

This is one of three implementations — see the
[project README](../README.md) for the broader context, and the
[Phase 3 retrospective](../docs/retrospectives/phase-3-retrospective.md)
for a side-by-side comparison with Phase 2 (and the cross-phase
patterns that ported).

## Architecture summary

Custom `BaseAgent` orchestrator coordinating ADK workflow agents:
a `ParallelAgent` for concurrent research, two `LoopAgent`s for
audit retry loops, plus a final assembly agent with
`output_schema=FinalBrief`.

```
PhaseThreeOrchestrator (custom BaseAgent)
├── fetch_price            ← direct tool call, no LLM
├── ParallelAgent          ← concurrent research
│   ├── research_news      ← google_search grounding
│   ├── research_catalysts ← google_search grounding
│   └── research_geo       ← google_search grounding
├── synthesise             ← initial synthesis
├── LoopAgent (synthesis audit, max 2 iterations)
│   ├── cross_check        ← auditor, calls exit_loop on PASS
│   └── synthesise_revise  ← targeted re-synthesis on FAIL
├── draft                  ← initial render
├── LoopAgent (rendering audit, max 2 iterations)
│   ├── sense_check        ← auditor, calls exit_loop on PASS
│   └── revise             ← targeted re-render on FAIL
└── final_brief            ← output_schema=FinalBrief
```

Full design discussion:
[`docs/tutorials/phase-3/03-design.md`](../docs/tutorials/phase-3/03-design.md).
Deployment specifics:
[`docs/tutorials/phase-3/09-deployment.md`](../docs/tutorials/phase-3/09-deployment.md).

## Setup

```bash
cd phase3-vertex-gemini
uv sync
```

Set up the environment file (not checked in):

```bash
cp env-example.txt .env
# Fill in:
#   GOOGLE_CLOUD_PROJECT=carty-470812
#   GOOGLE_CLOUD_LOCATION=us-central1
#   GOOGLE_GENAI_USE_VERTEXAI=1
```

Authentication uses Application Default Credentials:

```bash
gcloud auth application-default login
gcloud config set project carty-470812
```

Then verify the setup:

```bash
uv run python verify-setup.py
```

## Running the agent locally

```bash
uv run python -m briefing_agent.smoke_orchestrator
```

Runs the full pipeline end-to-end against Gemini via Vertex AI.
Wall-clock time: ~120-150s per run (with run-to-run variance; see
the Phase 3 retrospective). Cost: a few cents of Gemini Flash
tokens.

## Deploying to Agent Engine

```bash
uv run python -m briefing_agent.deploy
```

Deploys the orchestrator to Vertex AI Agent Engine. Takes ~3
minutes. The script uses `cloudpickle.register_pickle_by_value`
to embed the package source into the pickle — required for `src/`
layout projects, since `extra_packages` doesn't put files on
`sys.path` in the remote container.

Once deployed, run the deployed smoke against the live resource:

```bash
uv run python -m briefing_agent.smoke_deployed_orchestrator
```

First (cold-start) invocation: ~141s. Subsequent runs should be
closer to local.

> **Cleanup reminder:** the deployed Agent Engine resource bills
> per vCPU-hour while deployed, even when idle. Undeploy when not
> actively testing. See the Phase 3 retrospective for the
> undeploy snippet.

## Smoke tests

No pytest suite. Validation is via manual smoke runners:

| Runner | Purpose |
|---|---|
| `smoke_fetch_price` | Plain tool sanity |
| `smoke_research_news` | News research specialist |
| `smoke_research_catalysts` | Catalysts research specialist |
| `smoke_research_geo` | Geopolitics research specialist |
| `smoke_research_parallel` | `ParallelAgent` running all three research streams concurrently |
| `smoke_synthesise` | Live chain: research × 3 → synthesise |
| `smoke_cross_check` | Live chain + cross_check pass + fail scenarios |
| `smoke_synthesis_loop` | `LoopAgent` exercising synthesis audit retry path |
| `smoke_draft` | Live chain → draft |
| `smoke_sense_check` | Live chain + sense_check pass + fail scenarios |
| `smoke_rendering_loop` | `LoopAgent` exercising rendering audit retry path |
| `smoke_orchestrator` | Full local pipeline end-to-end |
| `smoke_deployed_orchestrator` | Full pipeline against the deployed Agent Engine resource |

Run any of them with `uv run python -m briefing_agent.<runner>`.

## Project layout

```
phase3-vertex-gemini/
├── pyproject.toml
├── uv.lock
├── env-example.txt
├── verify-setup.py             # one-shot Vertex/Gemini auth check
├── docs/
│   └── observations.md         # build-period ADK findings
└── src/
    └── briefing_agent/
        ├── __init__.py
        ├── orchestrator.py     # custom BaseAgent subclass
        ├── runner.py           # local runner entry point
        ├── deploy.py           # Agent Engine deploy script
        ├── models.py           # FinalBrief Pydantic + PriceSnapshot
        ├── tools.py            # fetch_price + exit_loop
        ├── specialists/
        │   ├── research_news.py
        │   ├── research_catalysts.py
        │   ├── research_geo.py
        │   ├── synthesise.py       # initial + revise variants
        │   ├── cross_check.py
        │   ├── draft.py
        │   ├── sense_check.py
        │   ├── revise.py
        │   └── final_brief.py      # output_schema=FinalBrief
        ├── workflows/
        │   ├── research_parallel.py    # ParallelAgent wiring
        │   ├── synthesis_loop.py       # LoopAgent (cross_check)
        │   └── rendering_loop.py       # LoopAgent (sense_check)
        ├── prompts/                    # 9 markdown prompts
        └── smoke_*.py                  # 13 manual smoke runners
```

## Tutorial steps

The full coaching-mode walkthrough is in
[`../docs/tutorials/phase-3/`](../docs/tutorials/phase-3/),
STEP-01 through STEP-09.
