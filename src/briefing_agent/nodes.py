from typing import TypedDict, Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from briefing_agent.state import State
from briefing_agent.prompts import load_prompt
from briefing_agent.data_sources.prices import PriceDataSource

class ResearchPlan(TypedDict):
    price: str
    news: str
    catalysts: str
    geopolitics: str

def plan(state: State) -> dict:
    print("-> Plan")
    target_date = state["target_date"]
    commodity = state["commodity"]
    briefing_spec = state["briefing_spec"]
    
    prompt = load_prompt("plan", target_date=target_date, commodity=commodity, briefing_spec=briefing_spec)
    
    model = ChatAnthropic(model="claude-haiku-4-5")
    structured_model = model.with_structured_output(ResearchPlan)
    response = structured_model.invoke([HumanMessage(content=prompt)])
    
    return {"research_plan": response}

def research_price(state: State) -> dict:
    print("-> Research Price")
    
    symbol = "CL=F"  # WTI crude futures, hardcoded for now
    source = PriceDataSource()
    price_data = source.fetch(symbol)
    
    return {"price_research": price_data}

class NewsItem(TypedDict):
    headline: str
    source: str
    url: str
    why_it_matters: str
    direction: Literal["supports_trend", "reverses_trend", "neutral"]
    timeframe: Literal["short_term", "structural"]


class NewsResearch(TypedDict):
    items: list[NewsItem]


def research_news(state: State) -> dict:
    print("-> Research News")
    
    target_date = state["target_date"]
    commodity = state["commodity"]
    instructions = state["research_plan"]["news"]
    
    prompt = load_prompt(
        "news",
        target_date=target_date,
        commodity=commodity,
        instructions=instructions,
    )
    
    web_search_tool = {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 5,
    }
    
    agent = create_agent(
        model="anthropic:claude-haiku-4-5",
        tools=[web_search_tool],
        response_format=NewsResearch,
    )
    
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    
    return {"news_research": result["structured_response"]}

def research_catalysts(state: State) -> dict:
    print("-> Research Catalysts")
    return {}

def research_geo(state: State) -> dict:
    print("-> Research Geopolitics")
    return {}

def synthesise(state: State) -> dict:
    print("-> Synthesise")
    return {}

def cross_check(state: State) -> dict:
    print("-> Cross-check")
    return {"cross_check_result": {"passed": True}, "cross_check_attempts": state.get("cross_check_attempts", 0) + 1}

def re_research(state: State) -> dict:
    print("-> Re-research")
    return {}

def draft(state: State) -> dict:
    print("-> Draft")
    return {}

def sense_check(state: State) -> dict:
    print("-> Sense-check")
    return {"sense_check_result": {"passed": True}, "sense_check_attempts": state.get("sense_check_attempts", 0) + 1}

def revise(state: State) -> dict:
    print("-> Revise")
    return {}

def deliver(state: State) -> dict:
    print("-> Deliver")
    return {}
