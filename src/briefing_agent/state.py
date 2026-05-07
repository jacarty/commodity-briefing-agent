from typing import TypedDict, Annotated
from operator import add


class State(TypedDict):
    target_date: str
    commodity: str
    briefing_spec: dict
    research_plan: dict
    price_research: str
    news_research: str
    catalyst_research: str
    geo_research: str
    errors: Annotated[list[str], add]
    synthesis: str
    cross_check_result: dict
    re_research_targets: list[str]
    research_feedback: dict
    cross_check_attempts: int
    draft: str
    sense_check_result: dict
    revision_notes: list[str]
    sense_check_attempts: int
    final_brief: str
