#!/usr/bin/env python3
"""Curriculum authoring script — generates L0 and L1 lesson JSON via Claude.

Usage:
  python scripts/author_curriculum.py              # generate all missing lessons
  python scripts/author_curriculum.py --levels L0  # L0 only
  python scripts/author_curriculum.py --overwrite  # regenerate even if file exists
  python scripts/author_curriculum.py --dry-run    # print prompts, don't call API

Each generated file is validated against the Activity Pydantic schema before
being written.  Existing files are skipped unless --overwrite is passed, so
human-reviewed content is never overwritten by accident.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import anthropic
from englo.models import Activity, LessonFile, Level, Lesson

_CURRICULUM_DIR = Path(__file__).parent.parent / "englo" / "curriculum"

# ── Lesson plan ───────────────────────────────────────────────────────────────

LESSON_PLAN: list[dict] = [
    # ── L0: Bootstrap (pre-A1, hindi_support=0.8) ────────────────────────────
    {
        "file": "l0_lesson3.json",
        "level_id": "L0", "lesson_id": "L0-3",
        "title": "Colors",
        "cefr": "pre-A1", "hindi_support": 0.8,
        "simplicity_level": "L0", "accent_setting": "slow_clear",
        "topic": (
            "Basic colors: red, blue, green, yellow, white, black, orange, pink. "
            "Activities: learner hears and repeats each color, then translates "
            "Hindi color names to English, then answers 'What color is this?' "
            "with a single-word reply. Keep all target phrases to 1-3 words."
        ),
    },
    {
        "file": "l0_lesson4.json",
        "level_id": "L0", "lesson_id": "L0-4",
        "title": "Family Members",
        "cefr": "pre-A1", "hindi_support": 0.8,
        "simplicity_level": "L0", "accent_setting": "slow_clear",
        "topic": (
            "Family vocabulary: mother, father, sister, brother, grandmother, grandfather. "
            "Activities: repeat each word, translate Hindi family words to English, "
            "respond to 'Who is this?' with one word. 1-2 word targets only."
        ),
    },
    {
        "file": "l0_lesson5.json",
        "level_id": "L0", "lesson_id": "L0-5",
        "title": "Common Objects",
        "cefr": "pre-A1", "hindi_support": 0.8,
        "simplicity_level": "L0", "accent_setting": "slow_clear",
        "topic": (
            "Classroom/home objects: book, pen, chair, table, bag, water, door, window. "
            "Activities: repeat each word, translate from Hindi, point-and-name responses. "
            "Single word or short phrase targets."
        ),
    },
    {
        "file": "l0_lesson6.json",
        "level_id": "L0", "lesson_id": "L0-6",
        "title": "Food and Drinks",
        "cefr": "pre-A1", "hindi_support": 0.8,
        "simplicity_level": "L0", "accent_setting": "slow_clear",
        "topic": (
            "Basic food and drink: water, tea, rice, bread, apple, milk, egg, banana. "
            "Activities: repeat names, translate from Hindi, answer 'What do you want?' "
            "with a single food/drink word."
        ),
    },
    {
        "file": "l0_lesson7.json",
        "level_id": "L0", "lesson_id": "L0-7",
        "title": "Days of the Week",
        "cefr": "pre-A1", "hindi_support": 0.8,
        "simplicity_level": "L0", "accent_setting": "slow_clear",
        "topic": (
            "Days: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday. "
            "Activities: repeat each day, translate Hindi day names, sequence drills "
            "('What comes after Monday?'). Keep responses to one word."
        ),
    },
    {
        "file": "l0_lesson8.json",
        "level_id": "L0", "lesson_id": "L0-8",
        "title": "L0 Review — Words and Short Phrases",
        "cefr": "pre-A1", "hindi_support": 0.8,
        "simplicity_level": "L0", "accent_setting": "slow_clear",
        "topic": (
            "Consolidation of all L0 vocabulary: mix of color + family + object + food + "
            "day words. Include 2 recall_drill activities (type must be 'recall_drill') "
            "and 3-4 listen_repeat. Target: single words and very short phrases "
            "(e.g. 'red apple', 'my mother', 'Monday morning')."
        ),
    },
    # ── L1: First Sentences (A1, hindi_support=0.5) ──────────────────────────
    {
        "file": "l1_lesson1.json",
        "level_id": "L1", "lesson_id": "L1-1",
        "title": "I am / You are / He is",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Present tense 'to be': I am, you are, he is, she is, it is, we are, they are. "
            "Activities: repeat contracted forms (I'm, you're, he's), translate Hindi "
            "sentences using 'hoon/hai/hain', answer 'Who are you?' with 'I am [name].' "
            "Targets are full simple sentences (5-8 words)."
        ),
    },
    {
        "file": "l1_lesson2.json",
        "level_id": "L1", "lesson_id": "L1-2",
        "title": "Likes and Dislikes",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Simple present: I like, I don't like, I love, I hate. "
            "Targets: 'I like tea.', 'I don't like cold weather.', 'I love cricket.' "
            "Include prompt_respond: 'What do you like?' learner answers in a full sentence. "
            "Hindi scaffolding at ~50%: use Hindi for instructions, English for targets."
        ),
    },
    {
        "file": "l1_lesson3.json",
        "level_id": "L1", "lesson_id": "L1-3",
        "title": "Talking About Your Family",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Full sentences about family: 'My mother is a teacher.', 'I have one brother.', "
            "'My father works in Delhi.', 'She is my sister.' "
            "Include 'have' sentences and simple possessives. "
            "prompt_respond: 'Tell me about your family.' Learner gives one sentence."
        ),
    },
    {
        "file": "l1_lesson4.json",
        "level_id": "L1", "lesson_id": "L1-4",
        "title": "Can I Have...? — Requests",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Polite requests: 'Can I have some water, please?', 'Can you help me?', "
            "'Please give me the book.', 'May I sit here?' "
            "Include a roleplay-style prompt_respond: tutor plays shopkeeper, "
            "learner asks for an item. Hindi scaffolding at 50%."
        ),
    },
    {
        "file": "l1_lesson5.json",
        "level_id": "L1", "lesson_id": "L1-5",
        "title": "Where Is...? — Locations",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Location questions and answers: 'Where is the school?', 'It is near the market.', "
            "'The shop is on the left.', 'Go straight and turn right.' "
            "Prepositions: in, on, near, next to, opposite. "
            "prompt_respond: 'Where do you live?' Learner gives a simple answer."
        ),
    },
    {
        "file": "l1_lesson6.json",
        "level_id": "L1", "lesson_id": "L1-6",
        "title": "Shopping — Prices and Quantities",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Shopping language: 'How much is this?', 'It costs fifty rupees.', "
            "'I want two kilos of rice.', 'That is too expensive.', 'I will take it.' "
            "Include number+noun phrases and a short roleplay prompt_respond."
        ),
    },
    {
        "file": "l1_lesson7.json",
        "level_id": "L1", "lesson_id": "L1-7",
        "title": "Daily Routine",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Simple present for routines: 'I wake up at seven.', 'I eat breakfast.', "
            "'I go to work by bus.', 'I come home at six.', 'I sleep at ten.' "
            "Time expressions: in the morning, in the evening, at night. "
            "prompt_respond: 'What do you do in the morning?'"
        ),
    },
    {
        "file": "l1_lesson8.json",
        "level_id": "L1", "lesson_id": "L1-8",
        "title": "L1 Review — Simple Conversations",
        "cefr": "A1", "hindi_support": 0.5,
        "simplicity_level": "L1", "accent_setting": "slow_clear",
        "topic": (
            "Consolidation: mix all L1 grammar (to be, like, have, can, where, routine). "
            "Include a short 3-turn roleplay scenario (meeting someone new, asking where "
            "they are from, what they do). Activity types: listen_repeat (2), "
            "translate_say (2), prompt_respond (3). Full sentences throughout."
        ),
    },
]

# ── Prompt template ───────────────────────────────────────────────────────────

_ACTIVITY_SCHEMA = """
{
  "id": "string — e.g. 'L0-3-A1'",
  "type": "one of: listen_repeat | translate_say | prompt_respond | recall_drill",
  "target_text": "the English text the learner must produce (natural, correct English)",
  "hindi_scaffold": "Hindi instructions/hint in Devanagari — e.g. 'सुनिए और दोहराइए: Red.'",
  "expected_pattern": "lowercase, punctuation-stripped version of the key words",
  "success_criteria": "e.g. 'pronunciation_accuracy >= 0.7 and utterance_complete'",
  "accent_setting": "slow_clear | normal_clear",
  "simplicity_level": "L0 | L1 | L2 | L3 | L4",
  "hindi_support": 0.0 to 1.0,
  "vocab_introduced": ["only new words appearing for the first time in this lesson"]
}
"""

_PROMPT_TEMPLATE = """\
You are an expert English curriculum designer for Hindi-speaking absolute beginners in tier-2/3 Indian cities.

Generate a complete lesson as a valid JSON object with this exact top-level structure:
{{
  "level": {{
    "id": "{level_id}",
    "name": "{level_name}",
    "cefr": "{cefr}",
    "hindi_support": {hindi_support},
    "accent_setting": "{accent_setting}"
  }},
  "lesson": {{
    "id": "{lesson_id}",
    "level_id": "{level_id}",
    "title": "{title}",
    "activities": [ ... 6 to 8 Activity objects ... ]
  }}
}}

Each Activity object must match this schema exactly:
{activity_schema}

Topic and content requirements for this lesson:
{topic}

Strict rules:
1. Return ONLY valid JSON — no prose, no markdown fences, no extra keys.
2. Hindi scaffold must use proper Devanagari script (not romanised Hindi).
3. For listen_repeat: hindi_scaffold = "सुनिए और दोहराइए: <target_text>"
4. For translate_say: hindi_scaffold gives the Hindi phrase to translate TO English.
5. For prompt_respond: hindi_scaffold gives a Hindi hint about what to say.
6. All target_text must be correct, natural English — no grammar errors.
7. Activities must be ordered easy → harder within the lesson.
8. vocab_introduced: only list words genuinely new in this lesson (not re-listed each time).
9. success_criteria for listen_repeat: "pronunciation_accuracy >= 0.7 and utterance_complete"
   success_criteria for translate_say: "correct_vocabulary and pronunciation_accuracy >= 0.65"
   success_criteria for prompt_respond: "correct_meaning and utterance_complete"
   success_criteria for recall_drill: "pronunciation_accuracy >= 0.65 and utterance_complete"
10. hindi_support = {hindi_support}, simplicity_level = "{simplicity_level}", accent_setting = "{accent_setting}"
"""


# ── Generator ─────────────────────────────────────────────────────────────────

def _build_prompt(plan: dict) -> str:
    level_names = {"L0": "Bootstrap", "L1": "First Sentences", "L2": "Everyday",
                   "L3": "Confident", "L4": "Fluency"}
    return _PROMPT_TEMPLATE.format(
        level_id=plan["level_id"],
        level_name=level_names[plan["level_id"]],
        cefr=plan["cefr"],
        lesson_id=plan["lesson_id"],
        title=plan["title"],
        hindi_support=plan["hindi_support"],
        accent_setting=plan["accent_setting"],
        simplicity_level=plan["simplicity_level"],
        topic=plan["topic"],
        activity_schema=_ACTIVITY_SCHEMA,
    )


def _validate_lesson(raw: dict, plan: dict) -> LessonFile:
    """Parse and validate via Pydantic; raises on any schema violation."""
    lf = LessonFile(**raw)
    assert len(lf.lesson.activities) >= 4, "Too few activities"
    for a in lf.lesson.activities:
        assert a.target_text.strip(), f"Empty target_text in {a.id}"
        assert a.hindi_scaffold.strip(), f"Empty hindi_scaffold in {a.id}"
    return lf


def generate_lesson(plan: dict, client: anthropic.Anthropic, dry_run: bool) -> str | None:
    """Generate one lesson JSON string.  Returns None on dry-run."""
    prompt = _build_prompt(plan)

    if dry_run:
        print(f"\n{'='*60}")
        print(f"DRY RUN: {plan['lesson_id']} — {plan['title']}")
        print(prompt[:400] + "…")
        return None

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line (```json or ```) and last line (```)
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        return "\n".join(inner)
    return text


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ENGLO curriculum JSON files")
    parser.add_argument("--levels", nargs="+", default=["L0", "L1"],
                        help="Levels to generate (default: L0 L1)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Regenerate even if file already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without calling the API")
    args = parser.parse_args()

    levels = set(args.levels)
    plans = [p for p in LESSON_PLAN if p["level_id"] in levels]

    if not args.dry_run:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
            sys.exit(1)
        client = anthropic.Anthropic(api_key=api_key)
    else:
        client = None  # type: ignore

    ok = skip = fail = 0

    for plan in plans:
        out_path = _CURRICULUM_DIR / plan["file"]

        if out_path.exists() and not args.overwrite:
            print(f"  SKIP  {plan['file']} (already exists; use --overwrite to regenerate)")
            skip += 1
            continue

        print(f"  GEN   {plan['lesson_id']} — {plan['title']} … ", end="", flush=True)

        raw_text = generate_lesson(plan, client, args.dry_run)
        if raw_text is None:
            continue

        try:
            raw_json = json.loads(_strip_fences(raw_text))
            lf = _validate_lesson(raw_json, plan)
            out_path.write_text(
                json.dumps(raw_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"OK ({len(lf.lesson.activities)} activities)")
            ok += 1
        except Exception as e:
            print(f"FAIL — {e}")
            # Write raw text for inspection even on validation failure
            (out_path.with_suffix(".raw.txt")).write_text(raw_text, encoding="utf-8")
            fail += 1

        # Polite pause between API calls
        if not args.dry_run:
            time.sleep(1)

    print(f"\nDone: {ok} generated, {skip} skipped, {fail} failed.")


if __name__ == "__main__":
    main()
