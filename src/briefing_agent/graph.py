from langgraph.graph import StateGraph, START, END
from briefing_agent.state import State
from briefing_agent.nodes import (
    plan, research_price, research_news, research_catalysts, research_geo,
    synthesise, cross_check, re_research,
    draft, sense_check, revise, deliver,
)

def route_after_cross_check(state: State) -> str:
    if state["cross_check_result"]["passed"]:
        return "passed"
    if state["cross_check_attempts"] >= 2:
        return "passed"
    return "failed"

def route_after_sense_check(state: State) -> str:
    if state["sense_check_result"]["passed"]:
        return "passed"
    else:
        return "failed"

def make_graph():
    graph_builder = StateGraph(State)
    
    # Add nodes
    graph_builder.add_node("plan", plan)
    graph_builder.add_node("research_price", research_price)
    graph_builder.add_node("research_news", research_news)
    graph_builder.add_node("research_catalysts", research_catalysts)
    graph_builder.add_node("research_geo", research_geo)
    graph_builder.add_node("synthesise", synthesise)
    graph_builder.add_node("cross_check", cross_check)
    graph_builder.add_node("re_research", re_research)
    graph_builder.add_node("draft", draft)
    graph_builder.add_node("sense_check", sense_check)
    graph_builder.add_node("revise", revise)
    graph_builder.add_node("deliver", deliver)
    
    # Add edges
    graph_builder.add_edge(START, "plan")
    graph_builder.add_edge("plan", "research_price")
    graph_builder.add_edge("plan", "research_news")
    graph_builder.add_edge("plan", "research_catalysts")
    graph_builder.add_edge("plan", "research_geo")
    graph_builder.add_edge("research_price", "synthesise")
    graph_builder.add_edge("research_news", "synthesise")
    graph_builder.add_edge("research_catalysts", "synthesise")
    graph_builder.add_edge("research_geo", "synthesise")
    graph_builder.add_edge("re_research", "synthesise")
    graph_builder.add_edge("synthesise", "cross_check")
    graph_builder.add_edge("draft", "sense_check")
    graph_builder.add_edge("revise", "sense_check")
    graph_builder.add_edge("deliver", END)

    # Add conditional edges
    graph_builder.add_conditional_edges(
        "cross_check",
        route_after_cross_check,
        {
            "passed": "draft",
            "failed": "re_research",
        },
    )

    graph_builder.add_conditional_edges(
        "sense_check",
        route_after_sense_check,
        {
            "passed": "deliver",
            "failed": "revise",
        },
    )

    # Compile and return
    return graph_builder.compile()
