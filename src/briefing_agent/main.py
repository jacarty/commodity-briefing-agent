from dotenv import load_dotenv

load_dotenv()

from briefing_agent.graph import make_graph

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

if __name__ == "__main__":
    run()
