from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

def load_prompt(name: str, **variables) -> str:
    """Load a prompt file by name and substitute variables.
    
    Example: load_prompt("plan", target_date="2026-05-07", commodity="crude_oil", briefing_spec=...)
    """
    path = PROMPTS_DIR / f"{name}.md"
    template = path.read_text()
    return template.format(**variables)
