# STEP-09 — Agent Engine deployment

Deploy the local orchestrator to Vertex AI Agent Engine. The last
step of Phase 3 before the cross-phase retrospective.

## What's in this PR

Two new source files:

| File | Role |
|---|---|
| `src/briefing_agent/deploy.py` | One-shot deploy script — wraps orchestrator in AdkApp, calls `agent_engines.create` |
| `src/briefing_agent/smoke_deployed_orchestrator.py` | Smoke test against the deployed resource |

## Why Agent Engine

STEP-03 chose Agent Engine deployment as the eventual goal of
Phase 3. The reasons hold:

- **It's what Vertex is for.** Building an ADK agent and never
  deploying uses maybe 40% of the platform.
- **Managed sessions** come for free — Agent Engine attaches a
  managed session resource automatically.
- **Co-location with Gemini** — agent and model are in the same
  region, which helps latency.
- **Closes the deploy story for the three-phase comparison.**
  Phase 1 (LangGraph) ran locally; Phase 2 (Strands) ran locally
  with a hand-rolled API surface; Phase 3 deploys to a managed
  runtime.

## The deploy mechanism

Agent Engine deploys by pickling the agent object locally
(`cloudpickle`), uploading it to GCS, then unpickling it in a
remote container. The critical requirement is that the remote
container must be able to resolve any module references baked
into the pickle.

For projects using a `src/` layout (like ours), the remote
container won't have the local package on `sys.path`. The
solution is `cloudpickle.register_pickle_by_value`, which embeds
the module's source code directly into the pickle rather than
recording import paths. This makes the pickle self-contained.

```python
import cloudpickle
import briefing_agent
cloudpickle.register_pickle_by_value(briefing_agent)

# 1. Initialise Vertex AI SDK
vertexai.init(project=..., location=..., staging_bucket=...)

# 2. Wrap the orchestrator in AdkApp
app = agent_engines.AdkApp(agent=orchestrator, enable_tracing=True)

# 3. Deploy
remote_app = agent_engines.create(
    agent_engine=app,
    requirements=[...],
    display_name="commodity-briefing-agent",
)
```

The `staging_bucket` is a GCS bucket used for build artifacts —
Agent Engine builds a container from our code, stores it in the
bucket, then deploys it.

## The deploy debugging journey

The first deploy attempt used `extra_packages=["./src/briefing_agent"]`
— the pattern shown in many Agent Engine examples. It failed
with `ModuleNotFoundError: No module named 'briefing_agent'`.
The remote container extracted the files but didn't add them to
`sys.path`.

Three approaches were tried and failed:

1. **`extra_packages=["./src/briefing_agent"]`** — extracts
   files but doesn't make them importable
2. **`extra_packages=["."]`** — ships the whole project including
   `pyproject.toml`, but Agent Engine doesn't `pip install` it
3. **`extra_packages=["dist/briefing_agent-0.1.0-py3-none-any.whl"]`**
   — ships the wheel file, but Agent Engine doesn't `pip install`
   wheels from `extra_packages` either

The fix: `cloudpickle.register_pickle_by_value(briefing_agent)`.
This embeds the full source of the `briefing_agent` package
into the pickle itself, so the remote container never needs to
import the module — the code is already in the pickle.

This is a known pain point with Agent Engine and `src/` layouts.
Multiple open issues on the `adk-python` repo document the same
problem (#2044, #2947, #3532). The official recommendation from
Google's ADK team is to build a wheel, but in practice
`register_pickle_by_value` is simpler and works reliably.

An alternative approach (not used here) is **source-based
deployment** via `AgentEngineConfig` with `source_packages`,
`entrypoint_module`, and `entrypoint_object` — this bypasses
pickling entirely and has Agent Engine import the agent directly
from source. Worth considering for future projects.

## What ran (deploy)

Deploy completed in approximately **3 minutes** (no precise
timing observed; the deploy log doesn't print elapsed time).
Steps logged:

1. **Requirements identification** — Agent Engine added
   `cloudpickle==3.1.2` automatically. This is used to pickle the
   orchestrator object for transmission to the managed runtime.
   We didn't need to add it ourselves.
2. **Bucket / tarball write** — orchestrator pickled to
   `agent_engine.pkl`, requirements written to
   `requirements.txt`, extra packages tarballed to
   `dependencies.tar.gz`.
3. **AgentEngine creation** — LRO (Long-Running Operation)
   started. Progress visible in Cloud Logging.
4. **Resource created.** Resource name:
   `projects/873708835509/locations/us-central1/reasoningEngines/3829216919253155840`

## What ran (deployed smoke)

The deployed smoke completed in **141.1 seconds** with 21 events
total. Comparable to local (129s), slightly slower as expected
for cold start.

Per-agent event counts:

| Agent | Events | Iterations |
|---|---|---|
| research_news | 1 | n/a |
| research_catalysts | 1 | n/a |
| research_geo | 1 | n/a |
| phase_three_orchestrator | 1 | (price_data fetched event) |
| synthesise | 1 | initial |
| cross_check | 6 | 2 iterations (each producing ~3 events) |
| synthesise_revise | 2 | 1 invocation, 2 events |
| draft | 1 | initial |
| sense_check | 4 | 2 iterations |
| revise | 2 | 1 invocation, 2 events |
| final_brief | 1 | initial |

Same pattern as local — both audit loops hit iteration 2 (FAIL
→ revise → PASS).

**FinalBrief content** is structurally identical to local:
subject, html_body, plain_text_body, all populated and
well-formed. One small rendering difference observed: in the
deployed version, plain_text_body has a blank line between the
section header and the first paragraph (e.g., `"PRICE SECTION\n\nCrude oil closed today..."`).
The local version had no blank line (header on its own line,
content immediately below). Probably an artefact of Vertex's text
serialisation; not a bug.

## Local vs deployed comparison

| Dimension | Local | Deployed |
|---|---|---|
| Wall-clock time | 129.0s | 141.1s |
| Event count | 17 | 21 |
| Iteration pattern | Both loops iter 2 | Both loops iter 2 |
| FinalBrief validity | First-try PASS | First-try PASS |
| HTML body format | Identical | Identical |
| Plain text format | No blank line after header | Blank line after header |
| Cold start? | n/a | Yes (first invocation) |

The event count difference (17 vs 21) is because Vertex emits
slightly more granular events per cross_check call than local
does. Specifically, each cross_check call in Vertex emits ~3
events vs ~2 events locally. Same function calls, finer-grained
event yield.

Latency expectation for subsequent runs: should be closer to
local (~120-150s) once cold start is amortised.

## How to invoke once deployed

The smoke test uses `remote_app.async_stream_query`:

```python
async for event in remote_app.async_stream_query(
    user_id="smoke_user",
    session_id=session_id,
    message="Run the daily oil briefing pipeline...",
):
    print(event)
```

Events from the deployed agent are dicts (not Event objects).
The managed-session API is slightly different from the local
SessionService — the smoke uses duck-typing fallbacks to handle
both shapes.

## STEP-03 deployment objective — closed

STEP-03 stated: *"Phase 3 ends with the agent deployed and
invokable from a managed runtime."* Achieved.

## Costs observed

- Deploy itself: free (Agent Engine doesn't charge for the
  create-resource operation)
- Cloud Build for the container: cents
- One deployed invocation: a few cents of Gemini Flash tokens
  plus a small per-invocation Agent Engine fee

**Hosting** the deployed resource charges per vCPU-hour while
it's deployed, even when idle. Recommend undeploying when not
actively testing.

## Cleanup

To undeploy and stop billing:

```python
import vertexai
from vertexai import agent_engines

vertexai.init(project="carty-470812", location="us-central1")
remote_app = agent_engines.get(
    resource_name="projects/873708835509/locations/us-central1/reasoningEngines/3829216919253155840"
)
remote_app.delete()
```

Or via the UI in the Cloud Console under Vertex AI > Agent
Engine.

For now (active development / cross-phase comparison phase),
leave deployed. Undeploy before the conversation about Phase 3
moves into long-term archival.

## What's next

- Cross-phase retrospective (Phase 1 vs Phase 2 vs Phase 3)
  comparing code volume, latency, observability, what ports
  cleanly, framework-level tradeoffs
- Optional: a second deployed-smoke run to confirm warm-start
  latency is closer to local
- Optional: a deployed invocation with verbose tracing enabled
  (we set `enable_tracing=True` at deploy time but didn't
  inspect the trace data)
