"""Phase 3 orchestrator.

Custom BaseAgent subclass that coordinates the full pipeline:

  1. parallel research (news + catalysts + geo)
  2. fetch_price (direct function call, no LLM)
  3. initial synthesise
  4. synthesis_loop (cross_check + revise, max 2 iterations)
  5. initial draft
  6. rendering_loop (sense_check + revise, max 2 iterations)
  7. final_brief assembly (with output_schema retry on validation error)

Why custom BaseAgent and not SequentialAgent: ADK's LoopAgent
propagates `escalate=True` upward to halt its parent. A naive
SequentialAgent containing two LoopAgents would halt the moment
synthesis_loop exits, never running rendering_loop. The custom
orchestrator absorbs the escalate signal between loops so the
pipeline continues. This is the documented community-recommended
workaround for adk-python#1376.

Escalate suppression:

    async for event in self.synthesis_loop.run_async(ctx):
        if event.actions:
            event.actions.escalate = False
        yield event

Same treatment after rendering_loop. After both loops, the
escalate signal has done its job (loop exited) and shouldn't
propagate further.

State writes from custom agents:

The orchestrator writes state['price_data'] directly. In ADK,
state mutations from a custom BaseAgent must flow through
`event.actions.state_delta` to be persisted into the canonical
session state. Direct assignment to `ctx.session.state[key]`
works transiently for downstream agents in the same invocation
but doesn't always survive into the final session view. The
state_delta path is the canonical mechanism.

The first version of this orchestrator (pre-fix) did direct
assignment only; the smoke ran successfully end-to-end (synthesise
saw price_data via template substitution and produced grounded
output), but inspecting state at the end showed price_data
missing. The fix below uses state_delta, which both writes the
key visibly downstream AND persists it into the final session.

FinalBrief validation retry:

The final_brief specialist uses output_schema=FinalBrief. If the
model produces invalid JSON, ADK raises pydantic.ValidationError.
We catch it, re-run the specialist once, and let any second
error propagate.
"""

from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import ValidationError

from briefing_agent.tools import fetch_price


class PhaseThreeOrchestrator(BaseAgent):
    """Top-level orchestrator for the Phase 3 commodity briefing agent.

    All sub-agents are passed in at construction. The orchestrator
    builds the pipeline order programmatically in _run_async_impl.
    """

    research_parallel: ParallelAgent
    synthesise: LlmAgent
    synthesis_loop: LoopAgent
    draft: LlmAgent
    rendering_loop: LoopAgent
    final_brief: LlmAgent

    def __init__(
        self,
        name: str,
        research_parallel: ParallelAgent,
        synthesise: LlmAgent,
        synthesis_loop: LoopAgent,
        draft: LlmAgent,
        rendering_loop: LoopAgent,
        final_brief: LlmAgent,
    ):
        super().__init__(
            name=name,
            research_parallel=research_parallel,
            synthesise=synthesise,
            synthesis_loop=synthesis_loop,
            draft=draft,
            rendering_loop=rendering_loop,
            final_brief=final_brief,
            sub_agents=[
                research_parallel,
                synthesise,
                synthesis_loop,
                draft,
                rendering_loop,
                final_brief,
            ],
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the full pipeline. Yields events from each stage."""
        # ====================================================
        # STAGE 1: Parallel research
        # ====================================================
        async for event in self.research_parallel.run_async(ctx):
            yield event

        # ====================================================
        # STAGE 2: fetch_price (direct function call)
        # ====================================================
        # fetch_price is deterministic. The orchestrator calls it
        # directly and writes the result to state via state_delta.
        # Direct assignment to ctx.session.state[key] alone is not
        # sufficient — the state_delta path is what persists.
        price_data = fetch_price()
        price_data_str = str(price_data)

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=(
                            f"price_data fetched: "
                            f"{price_data['symbol']} @ "
                            f"${price_data['last_close']:.2f} "
                            f"on {price_data['last_close_date']}"
                        )
                    )
                ],
            ),
            actions=EventActions(state_delta={"price_data": price_data_str}),
        )

        # Belt-and-braces: also write to session.state directly so
        # downstream agents in this invocation see the value
        # immediately (state_delta is applied async by the session
        # service; the SessionService docs note state_delta is the
        # authoritative path but immediate access matters).
        ctx.session.state["price_data"] = price_data_str

        # ====================================================
        # STAGE 3: Initial synthesise
        # ====================================================
        async for event in self.synthesise.run_async(ctx):
            yield event

        # ====================================================
        # STAGE 4: synthesis_loop (cross_check + revise)
        # ====================================================
        # The LoopAgent escalate signal would otherwise halt the
        # orchestrator. We absorb it so the pipeline continues.
        async for event in self.synthesis_loop.run_async(ctx):
            if event.actions is not None and event.actions.escalate:
                event.actions.escalate = False
            yield event

        # ====================================================
        # STAGE 5: Initial draft
        # ====================================================
        async for event in self.draft.run_async(ctx):
            yield event

        # ====================================================
        # STAGE 6: rendering_loop (sense_check + revise)
        # ====================================================
        async for event in self.rendering_loop.run_async(ctx):
            if event.actions is not None and event.actions.escalate:
                event.actions.escalate = False
            yield event

        # ====================================================
        # STAGE 7: final_brief assembly (with retry on validation error)
        # ====================================================
        try:
            async for event in self.final_brief.run_async(ctx):
                yield event
        except ValidationError as first_error:
            yield Event(
                author=self.name,
                invocation_id=ctx.invocation_id,
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                f"final_brief validation failed: "
                                f"{first_error.error_count()} errors. "
                                f"Retrying once."
                            )
                        )
                    ],
                ),
            )
            async for event in self.final_brief.run_async(ctx):
                yield event


def build_orchestrator() -> PhaseThreeOrchestrator:
    """Build the orchestrator with all sub-agents."""
    from briefing_agent.specialists.draft import build_draft
    from briefing_agent.specialists.final_brief import build_final_brief
    from briefing_agent.specialists.synthesise import build_synthesise
    from briefing_agent.workflows.rendering_loop import build_rendering_loop
    from briefing_agent.workflows.research_parallel import build_research_parallel
    from briefing_agent.workflows.synthesis_loop import build_synthesis_loop

    return PhaseThreeOrchestrator(
        name="phase_three_orchestrator",
        research_parallel=build_research_parallel(),
        synthesise=build_synthesise(),
        synthesis_loop=build_synthesis_loop(),
        draft=build_draft(),
        rendering_loop=build_rendering_loop(),
        final_brief=build_final_brief(),
    )
