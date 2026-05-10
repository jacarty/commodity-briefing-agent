"""Hello-world Bedrock invocation via Strands.

Proves that the Strands SDK + Bedrock + auth chain all work end-to-end.
This is NOT the agent — it's a smoke test you can rerun any time the
environment feels off.

Run with:
    uv run python -m briefing_agent.hello

If `verify_setup.py` passes but this fails, the problem is Strands-specific
(SDK version, BedrockModel config) rather than environment-level.
"""

import os

from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel

load_dotenv()

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"


def main() -> None:
    region = os.getenv("AWS_REGION")
    print(f"Strands hello-world (model: {MODEL_ID}, region: {region})\n")

    model = BedrockModel(model_id=MODEL_ID, region_name=region)
    agent = Agent(
        model=model,
        system_prompt="You are a terse assistant. Reply in one short sentence.",
    )

    agent("Say hello and confirm you are running on Bedrock.")


if __name__ == "__main__":
    main()
