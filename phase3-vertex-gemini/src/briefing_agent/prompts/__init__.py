"""Prompt loading helper.

Reads markdown prompt files by name. Each prompt lives as a .md file
in this directory and is loaded with simple str.format() substitution.

Phase 1 and Phase 2 used the same pattern. Phase 3 keeps the convention
because prompt-as-file remains the right shape — markdown editor
support, diffable history, no source-file pollution. ADK has its own
prompt-management primitives but they don't add value over plain files
for our workflow.

Usage:
    from briefing_agent.prompts import load_prompt
    text = load_prompt("news")  # plain load, no substitution
    text = load_prompt("news", target_date="2026-05-10")  # with vars
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str, **kwargs: str) -> str:
    """Load a prompt by name and substitute any provided variables.

    Args:
        name: Prompt filename without the .md extension.
        **kwargs: Variables to substitute via str.format().

    Returns:
        The prompt text, with substitutions applied.

    Raises:
        FileNotFoundError: If <name>.md doesn't exist.
        KeyError: If the prompt references a variable that wasn't provided.
    """
    path = _PROMPTS_DIR / f"{name}.md"
    text = path.read_text()
    if kwargs:
        text = text.format(**kwargs)
    return text
