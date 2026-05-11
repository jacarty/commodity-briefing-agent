"""Chained smoke test for revise.

Tests revise the way the orchestrator will call it: as a follow-up
to a failed sense_check, using sense_check's real failure output
as the feedback input.

The flow:

1. Run the full upstream chain (research → synthesise → draft).
2. Corrupt the draft with a faithfulness violation (same pattern
   as smoke_sense_check).
3. Run sense_check on the corrupted draft. Expect VERDICT: FAIL
   with a non-trivial REVISION NOTES section.
4. Extract REVISION NOTES from sense_check's response.
5. Call revise with the corrupted draft + the revision notes +
   the synthesis as source-of-truth.
6. Print the original (uncorrupted) draft, the revised brief, and
   a per-section diff summary so the targeted-revision behaviour
   is mechanically verifiable.

Cost: roughly 4-7 cents per run (full chain + sense_check on
corrupted + revise).

Run with:
    uv run python -m briefing_agent.smoke_revise

Manual inspection — four checks:
- Does the revised NEWS SECTION no longer contain the injected
  corruption ("peace negotiations have produced a binding
  ceasefire framework")?
- Do PRICE SECTION, CATALYSTS SECTION, GEOPOLITICS SECTION come
  through largely verbatim (or with only trivial changes)?
- Does the per-section diff summary show NEWS as substantially
  changed and the others as substantially unchanged?
- Does the revised brief still have all four section headers in
  the right order?
"""

import difflib
import json
import os
import re
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.draft import build_draft
from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news
from briefing_agent.specialists.revise import build_revise
from briefing_agent.specialists.sense_check import build_sense_check
from briefing_agent.specialists.synthesise import build_synthesise
from briefing_agent.tools import fetch_price

load_dotenv()

BRIEFING_SPEC = (
    "Daily oil briefing for a desk of senior analysts. Four prose "
    "sections (price, news, catalysts, geopolitics). Voice: senior "
    "analyst briefing colleagues — direct, evidence-led, professional "
    "but not stuffy. Length: 2-4 paragraphs per section."
)

FAITHFULNESS_CORRUPTION = (
    "Today's news flow points to a clear bearish setup: peace "
    "negotiations have produced a binding ceasefire framework, and "
    "the Strait of Hormuz is set to reopen to full traffic within "
    "48 hours."
)

SECTION_HEADERS = [
    "PRICE SECTION",
    "NEWS SECTION",
    "CATALYSTS SECTION",
    "GEOPOLITICS SECTION",
]


def assemble_synthesise_input(target_date, price_data, news_text, catalysts_text, geo_text):
    return f"""Target date: {target_date}
Commodity: crude oil

Briefing specification:
{BRIEFING_SPEC}

Research outputs follow. Read across all four streams before
writing.

=== PRICE DATA ===
{json.dumps(price_data, indent=2)}

=== NEWS RESEARCH ===
{news_text}

=== CATALYSTS RESEARCH ===
{catalysts_text}

=== GEOPOLITICS RESEARCH ===
{geo_text}
"""


def assemble_draft_input(target_date, synthesis_text):
    return f"""Target date: {target_date}
Commodity: crude oil

Briefing specification:
{BRIEFING_SPEC}

=== SYNTHESIS TO RENDER ===
{synthesis_text}
"""


def assemble_sense_check_input(target_date, synthesis_text, draft_text):
    return f"""Target date: {target_date}
Commodity: crude oil

=== SYNTHESIS (SOURCE OF TRUTH) ===
{synthesis_text}

=== BRIEF TO REVIEW ===
{draft_text}
"""


def assemble_revise_input(target_date, synthesis_text, draft_text, revision_notes):
    return f"""Target date: {target_date}
Commodity: crude oil

=== SYNTHESIS (SOURCE OF TRUTH) ===
{synthesis_text}

=== CURRENT DRAFT ===
{draft_text}

=== REVISION NOTES FROM SENSE_CHECK ===
{revision_notes}
"""


def corrupt_draft(draft_text):
    pattern = re.compile(r"(NEWS SECTION\s*\n)", re.IGNORECASE)
    match = pattern.search(draft_text)
    if not match:
        return draft_text + f"\n\nCORRUPTED ADDITION: {FAITHFULNESS_CORRUPTION}\n"
    insert_at = match.end()
    return draft_text[:insert_at] + FAITHFULNESS_CORRUPTION + " " + draft_text[insert_at:]


def extract_revision_notes(sense_check_text):
    marker = "REVISION NOTES"
    idx = sense_check_text.find(marker)
    if idx == -1:
        return sense_check_text
    notes = sense_check_text[idx + len(marker) :].strip()
    return notes.lstrip("\n :")


def split_sections(brief_text: str) -> dict[str, str]:
    """Parse a brief into a dict of section_name -> section_content.

    Splits on the uppercase section headers. Tolerant of preamble
    before the first header (returns it under key '' if present).
    """
    sections: dict[str, str] = {}
    # Build a regex that matches any of the known section headers.
    pattern = re.compile(
        r"^(" + "|".join(re.escape(h) for h in SECTION_HEADERS) + r")\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(brief_text))
    if not matches:
        return {"": brief_text.strip()}

    # Preamble before the first header.
    if matches[0].start() > 0:
        sections[""] = brief_text[: matches[0].start()].strip()

    for i, match in enumerate(matches):
        section_name = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(brief_text)
        sections[section_name] = brief_text[start:end].strip()

    return sections


def section_similarity(a: str, b: str) -> float:
    """Return a similarity ratio in [0, 1] between two section strings."""
    return difflib.SequenceMatcher(None, a, b).ratio()


def print_diff_summary(original_sections: dict[str, str], revised_sections: dict[str, str]):
    """Print a per-section comparison summary.

    For each named section in either brief, prints the similarity
    ratio and a verdict label. Helps see at a glance which sections
    were modified vs passed through.
    """
    print("\n" + "=" * 60)
    print("PER-SECTION COMPARISON")
    print("=" * 60)
    print(f"{'Section':<22} {'Similarity':<12} Verdict")
    print("-" * 60)
    for header in SECTION_HEADERS:
        original = original_sections.get(header, "")
        revised = revised_sections.get(header, "")
        if not original and not revised:
            verdict = "missing in both"
            ratio = 0.0
        elif not original:
            verdict = "new in revised"
            ratio = 0.0
        elif not revised:
            verdict = "removed in revised"
            ratio = 0.0
        else:
            ratio = section_similarity(original, revised)
            if ratio >= 0.98:
                verdict = "verbatim"
            elif ratio >= 0.85:
                verdict = "trivial changes"
            elif ratio >= 0.50:
                verdict = "partial rewrite"
            else:
                verdict = "substantial rewrite"
        print(f"{header:<22} {ratio:>6.2%}      {verdict}")
    print("-" * 60)
    print(
        "Expected: NEWS SECTION shows substantial rewrite (the flagged change); "
        "others verbatim or trivial changes only."
    )


def main():
    today = date.today().isoformat()
    region = os.getenv("AWS_REGION")
    print(f"Chained smoke test for revise (region: {region})")
    print(f"Target date: {today}\n")

    print("[1/8] fetch_price...")
    price_data = fetch_price()
    print(f"      Last close: ${price_data['last_close']:.2f} on {price_data['last_close_date']}")

    print("[2/8] research_news...")
    news_text = str(
        build_research_news()(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the most important oil-related news from the last 24 hours."
        )
    )

    print("[3/8] research_catalysts...")
    catalysts_text = str(
        build_research_catalysts()(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the scheduled market-moving events for today."
        )
    )

    print("[4/8] research_geo...")
    geo_text = str(
        build_research_geo()(
            f"Target date: {today}. Commodity: crude oil. "
            f"Identify the structural and macro themes shaping the market."
        )
    )

    print("[5/8] synthesise...")
    synthesis_text = str(
        build_synthesise()(
            assemble_synthesise_input(today, price_data, news_text, catalysts_text, geo_text)
        )
    )

    print("[6/8] draft (the ORIGINAL, before corruption)...")
    original_draft = str(build_draft()(assemble_draft_input(today, synthesis_text)))

    print("[7/8] sense_check on corrupted draft (expecting FAIL)...")
    corrupted_draft = corrupt_draft(original_draft)
    sense_check_response = str(
        build_sense_check()(assemble_sense_check_input(today, synthesis_text, corrupted_draft))
    )
    print("\n--- sense_check output ---")
    print(sense_check_response)
    print("--- end sense_check ---\n")

    revision_notes = extract_revision_notes(sense_check_response)

    print("[8/8] revise (using sense_check's actual revision notes)...")
    revise_input = assemble_revise_input(today, synthesis_text, corrupted_draft, revision_notes)
    revised = str(build_revise()(revise_input))

    print("\n" + "=" * 60)
    print("ORIGINAL DRAFT (before corruption)")
    print("=" * 60)
    print(original_draft)

    print("\n" + "=" * 60)
    print("REVISED BRIEF")
    print("=" * 60)
    print(revised)

    # Per-section diff summary. Compare original draft (NOT
    # the corrupted version) against the revised brief — that's
    # the comparison that answers "did revise stay targeted?"
    original_sections = split_sections(original_draft)
    revised_sections = split_sections(revised)
    print_diff_summary(original_sections, revised_sections)

    print("\nFor reference, the corruption injected into NEWS SECTION was:")
    print(f"  {FAITHFULNESS_CORRUPTION!r}")
    print(
        "Manual check: NEWS should be 'substantial rewrite' or 'partial rewrite' "
        "(the injection was added then removed/replaced). Other sections should be "
        "'verbatim' or 'trivial changes' if revise stayed targeted."
    )


if __name__ == "__main__":
    main()
