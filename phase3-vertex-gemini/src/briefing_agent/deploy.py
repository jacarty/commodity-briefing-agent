"""Deploy PhaseThreeOrchestrator to Vertex AI Agent Engine.

Wraps the orchestrator in AdkApp and deploys via
agent_engines.create. The deployed resource will be reachable via
its resource name (projects/.../locations/.../reasoningEngines/...).

Pre-requisites (one-time setup):

  1. Vertex AI APIs enabled (done in STEP-02 via
     `gcloud services enable aiplatform.googleapis.com`)
  2. A Cloud Storage bucket for staging build artifacts. The default
     here uses `gs://<PROJECT_ID>-agent-engine-staging`. If you want
     a different bucket, override STAGING_BUCKET in .env.
  3. ADC quota project set (done in STEP-02 via
     `gcloud auth application-default set-quota-project`)

The deploy will take several minutes — Agent Engine builds a
container from the local code and uploads it. Once done, the
resource name is printed; you'll need it for the deploy smoke
test (smoke_deployed_orchestrator.py).

Run with:

    uv run python -m briefing_agent.deploy
"""

import os

from dotenv import load_dotenv

load_dotenv()

import cloudpickle  # noqa: E402

import briefing_agent  # noqa: E402

# Embed the briefing_agent source code directly into the pickle
# rather than recording module paths. This avoids the
# ModuleNotFoundError that occurs when Agent Engine unpickles
# the agent object — the remote container doesn't have our
# src/briefing_agent on sys.path, but with pickle-by-value the
# code is self-contained in the pickle file.
cloudpickle.register_pickle_by_value(briefing_agent)

import vertexai  # noqa: E402
from vertexai import agent_engines  # noqa: E402

from briefing_agent.orchestrator import build_orchestrator  # noqa: E402


def main() -> None:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ["GOOGLE_CLOUD_LOCATION"]
    staging_bucket = os.environ.get(
        "STAGING_BUCKET",
        f"gs://{project}-agent-engine-staging",
    )

    print(f"Project:        {project}")
    print(f"Location:       {location}")
    print(f"Staging bucket: {staging_bucket}")
    print()

    # Initialise Vertex AI SDK
    vertexai.init(
        project=project,
        location=location,
        staging_bucket=staging_bucket,
    )

    # Build the orchestrator (same factory used locally)
    print("Building orchestrator with all sub-agents...")
    orchestrator = build_orchestrator()

    # Wrap in AdkApp — Agent Engine's deployable wrapper
    print("Wrapping in AdkApp...")
    app = agent_engines.AdkApp(
        agent=orchestrator,
        enable_tracing=True,
    )

    # Deploy
    print("\nDeploying to Agent Engine (this takes several minutes)...")
    print("=" * 60)

    remote_app = agent_engines.create(
        agent_engine=app,
        requirements=[
            "google-cloud-aiplatform[agent_engines,adk]>=1.112",
            "google-adk==1.33.0",
            "google-genai==1.75.0",
            "python-dotenv>=1.0,<2.0",
            "pydantic>=2.0,<3.0",
            "yfinance>=0.2.40,<0.3.0",
        ],
        display_name="commodity-briefing-agent",
        description="Daily crude oil briefing agent — Phase 3 (Vertex AI / Gemini)",
    )

    print("=" * 60)
    print()
    print("✅ Deployment complete.")
    print()
    print(f"Resource name: {remote_app.resource_name}")
    print()
    print("Save this resource name — you'll need it to invoke the")
    print("deployed agent. Add to .env as DEPLOYED_AGENT_RESOURCE.")


if __name__ == "__main__":
    main()
