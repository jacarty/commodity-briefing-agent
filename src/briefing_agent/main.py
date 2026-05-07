from dotenv import load_dotenv

load_dotenv()

from briefing_agent.graph import make_graph  # noqa: E402


def run():
    graph = make_graph()
    initial_state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "briefing_spec": {"sections": ["price", "news", "catalysts", "geopolitics"]},
    }
    result = graph.invoke(initial_state)
    print(result.get("research_plan"))
    print(result.get("price_research"))
    print(result.get("news_research"))
    print(result.get("catalyst_research"))
    print(result.get("geo_research"))
    print(result.get("synthesis"))
    print(result.get("cross_check_result"))
    print(result.get("draft"))
    print(result.get("final_brief"))


if __name__ == "__main__":
    run()
