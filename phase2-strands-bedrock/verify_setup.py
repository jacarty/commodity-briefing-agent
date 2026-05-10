"""Verify Phase 2 setup is working end-to-end.

Checks, in order:
1. Required env vars are set
2. AWS credentials are valid (sts:GetCallerIdentity)
3. Bedrock model access is granted (list foundation models)
4. A real Bedrock invocation succeeds via the eu cross-region inference profile

Run with:
    uv run python verify_setup.py

Each check fails loudly with a specific message so you can tell which
layer is broken (env vs credentials vs model access vs invocation).
"""

import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

# Phase 2 uses Claude Haiku 4.5 via the eu cross-region inference profile.
# This ID is the inference profile, not the raw model ID.
MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

REQUIRED_ENV_VARS = ["AWS_PROFILE", "AWS_REGION", "TAVILY_API_KEY"]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def check_env() -> None:
    missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
    if missing:
        fail(f"missing env vars: {missing}. Copy .env.example to .env and fill in values.")
    print("PASS: env vars set")


def check_aws_credentials() -> None:
    try:
        identity = boto3.client("sts").get_caller_identity()
    except (BotoCoreError, ClientError) as e:
        fail(
            f"AWS credentials invalid or expired: {e}. "
            f"Run `aws sso login --profile {os.getenv('AWS_PROFILE')}` to refresh."
        )
    print(f"PASS: AWS credentials valid (account {identity['Account']})")


def check_bedrock_model_access() -> None:
    region = os.getenv("AWS_REGION")
    try:
        client = boto3.client("bedrock", region_name=region)
        response = client.list_foundation_models()
    except (BotoCoreError, ClientError) as e:
        fail(f"could not list Bedrock models in {region}: {e}")

    claude_models = [m for m in response["modelSummaries"] if "claude" in m["modelId"].lower()]
    if not claude_models:
        fail(
            f"no Claude models accessible in {region}. "
            "Request access in the Bedrock console: Model access → request access for Anthropic."
        )
    print(f"PASS: {len(claude_models)} Claude models accessible in {region}")


def check_bedrock_invoke() -> None:
    region = os.getenv("AWS_REGION")
    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        response = client.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": "Reply with exactly: ok"}]}],
            inferenceConfig={"maxTokens": 10},
        )
    except (BotoCoreError, ClientError) as e:
        fail(
            f"Bedrock invoke failed for {MODEL_ID} in {region}: {e}. "
            "Check that model access is granted for this specific model."
        )

    text = response["output"]["message"]["content"][0]["text"].strip()
    print(f"PASS: Bedrock invoke returned: {text!r}")


def main() -> None:
    print(f"Verifying Phase 2 setup (region: {os.getenv('AWS_REGION')})\n")
    check_env()
    check_aws_credentials()
    check_bedrock_model_access()
    check_bedrock_invoke()
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
