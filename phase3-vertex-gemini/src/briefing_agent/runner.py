"""Smoke-test runner helper.

Wraps the ADK Runner + Session + event-loop boilerplate so individual
smoke tests stay focused on the agent under test and the query.

ADK is async-first — `Runner.run_async` yields events, and we need to
walk the event stream to find the final response. That's three to four
lines of boilerplate per call site. Extracting it here keeps the smoke
tests readable.

This helper is for development/smoke use only. The real orchestrator
(STEP-08+) has its own event-handling logic.
"""

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def run_specialist(
    agent: LlmAgent,
    query: str,
    app_name: str = "phase3_smoke",
    user_id: str = "smoke_user",
) -> str:
    """Run a specialist agent on a single query, return the final response text.

    Builds a fresh InMemorySessionService and Runner per call — each
    smoke run is isolated, no cross-call state.

    Args:
        agent: The ADK LlmAgent to invoke.
        query: The user query (will be sent as the user message).
        app_name: Used to namespace the session. Defaults to "phase3_smoke".
        user_id: Used to identify the session user. Defaults to "smoke_user".

    Returns:
        The agent's final response as text.

    Raises:
        RuntimeError: If no final response was produced (e.g. the agent
            errored or returned nothing).
    """
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
    )

    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    final_response: str | None = None
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    if not final_response:
        raise RuntimeError(
            f"Agent {agent.name!r} did not produce a final response. "
            "Check upstream events for errors."
        )

    return final_response
