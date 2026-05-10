# STEP-02 — Environment setup and first Bedrock invocation

## What I did

- Set up SSO for the AWS account; configured a profile pointed at
  the role with Bedrock access in eu-west-1
- Requested and received Bedrock model access for Anthropic Claude
  in eu-west-1 (console: Bedrock → Model access)
- Scaffolded `phase2-strands-bedrock/` with its own `pyproject.toml`,
  initial dependencies, and Ruff config matching Phase 1
- Created `.env.example` documenting the three env vars Phase 2
  needs: `AWS_PROFILE`, `AWS_REGION`, `TAVILY_API_KEY`
- Wrote `verify_setup.py` — runnable any time the environment feels
  off; checks env vars, AWS credentials, Bedrock model access, and
  a real Bedrock invocation in that order
- Wrote a Strands hello-world (`src/briefing_agent/hello.py`) that
  invokes Claude Haiku 4.5 via the eu cross-region inference profile
- Confirmed end-to-end: `verify_setup.py` passes, hello-world
  prints a Claude response

## What I learned

### AWS setup is not optional and not trivial

Phase 1 needed one environment variable: `ANTHROPIC_API_KEY`. Phase
2 has a longer checklist:

1. AWS account with billing enabled
2. SSO configured for the account, with a profile for local dev
3. IAM permissions on that role to invoke Bedrock
4. Model access granted for Anthropic Claude in the chosen region
5. Tavily API key for web search

Skipping any of these produces failures that look like SDK errors
but are actually upstream problems. The verify-setup script exists
to make those failures unambiguous.

### Model access is a separate gate from IAM permission

Having IAM permission to invoke Bedrock is not sufficient to use a
specific model. Model access has to be explicitly granted in the
Bedrock console: Bedrock → Model access → request access for
Anthropic. Until that's granted, `bedrock-runtime invoke_model`
returns an `AccessDeniedException` with a confusingly generic
message.

When Bedrock returns access denied, three things to check in order:
IAM policy, model access, region availability. Two of those three
look like the same error from the SDK.

### Cross-region inference profiles are the default

The Claude Haiku 4.5 model ID for direct invocation looks like
`anthropic.claude-haiku-4-5-20251001-v1:0`. The eu cross-region
inference profile is `eu.anthropic.claude-haiku-4-5-20251001-v1:0`
— note the `eu.` prefix.

Picking the profile ID is the right default — capacity is better,
cost is the same, and you're insulated from single-region outages.
Direct model IDs are an option only if data residency requirements
force them.

### SSO replaces long-lived credentials

For local dev, the AWS credentials chain works like this:

```
.env → AWS_PROFILE=<name>
    ↓
aws sso login --profile <name>   (interactive; once per session)
    ↓
~/.aws/sso/cache/  (short-lived credentials)
    ↓
boto3.Session() picks them up automatically
```

`.env` doesn't store any AWS credentials — only the profile name.
The credentials live in the SSO cache and expire with the session.
This means leaked `.env` files don't leak AWS access.

For deployed agents in AgentCore Runtime, this changes — credentials
come from IAM roles attached to the runtime, not from `.env`. That's
a deployment-step concern, not a local-dev concern.

### A verify-setup script saves debugging time

The four failure classes (env, credentials, model access,
invocation) each fail at a different layer with a different fix.
Encoding the checks in a script means the next person to set this
up (including future-me on a new machine) can skip the debugging
path:

```bash
uv run python verify_setup.py
```

Each check fails loudly with a specific message naming the likely
fix. Running this is the first thing to do when anything Bedrock-y
looks broken.

### Strands streams to stdout by default

The hello-world worked first try, but the response printed twice:

```
Hello, I'm Claude running on AWS Bedrock.Hello, I'm Claude running on AWS Bedrock.
```

The cause: Strands' `Agent.__call__` (i.e., `agent("...")`) does two
things by default — streams the response to stdout as it generates,
and returns the response object. The script's `print(response)` then
printed it a second time.

Three options to handle this:

1. Drop the explicit `print(response)` and rely on the streamed
   output (fine for hello-world, awkward for real use)
2. Pass `stream=False` to suppress the streaming print and use
   `print(response)` for output (what real code probably wants)
3. Capture the response object and access its content fields
   directly (most explicit; needed if you want token counts or tool
   call info)

Worth knowing because most LangChain/Anthropic-direct code patterns
assume "invoke returns; you print." Strands' default is "invoke
streams *and* returns." Will affect how research specialist agents
are wired in later steps — we don't want every specialist call
streaming to stdout.

### Hello-world proves plumbing, not behaviour

`verify_setup.py` and `hello.py` together prove:

- `boto3` can authenticate via SSO
- The Bedrock service is reachable from this account in this region
- The specific model is accessible
- The Strands SDK can invoke it via `BedrockModel`

They don't prove anything about agents, tool use, structured output,
or the workflow design. Those come in subsequent steps. The point
of this step was to remove "is the environment broken?" as a
hypothesis when later steps fail.

## What surprised me

- The Strands streaming-by-default behaviour. I'd assumed
  invoke-and-return was universal. It isn't. This is the kind of
  SDK-specific quirk that you only learn by running the code.

## Open questions

- The Strands SDK is currently unpinned in `pyproject.toml`. After
  the first `uv sync` resolved a version (and hello-world confirmed
  it works), the version should be pinned exactly. Not done yet —
  follow-up commit.

- Cost monitoring during development is a real concern that wasn't
  in Phase 1. Anthropic-direct billing was simple; Bedrock + Tavily
  + AgentCore is three bills with three different shapes. Worth a
  CloudWatch dashboard or Cost Anomaly Detection setup at some
  point — not this step.

- AgentCore Runtime requires its own service role and configuration.
  Deferred until we deploy. STEP-02 covers what we need to start
  *building* locally; deployment setup is a later step.

- The Strands streaming behaviour will need to be controlled in
  research specialist agents — we don't want eight specialists all
  streaming to stdout when the orchestrator calls them in parallel.
  TBD how cleanly Strands lets us silence that.

## Glossary

- **Bedrock model access** — Per-account permission to invoke a
  specific model family. Requested in the Bedrock console, separate
  from IAM permissions.
- **Inference profile** — A model ID prefix (e.g., `eu.`) that
  routes invocations across multiple regions for capacity. The
  default for production-grade Bedrock use.
- **AWS SSO** — Single Sign-On for AWS access. Replaces long-lived
  IAM user access keys. Credentials expire with the session and
  live in `~/.aws/sso/cache/`, not in `.env`.
- **Strands streaming** — Default behaviour of `Agent.__call__`:
  prints the response to stdout as it generates *and* returns the
  response object. Will need controlling for non-interactive
  specialist calls.
