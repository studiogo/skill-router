#!/usr/bin/env python3
"""
skill-router-config-init — interactive wizard that generates a starter
~/.claude/skill-rules.json from curated category templates.

Run once after installation, then tune manually as your workflow grows.
"""
import datetime
import json
import shutil
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "skill-rules.json"

CATEGORIES: dict[str, dict] = {
    "content-creation": {
        "label": "Content creation (LinkedIn, carousels, posts, newsletters)",
        "skills": {
            "create-carousel": {
                "keywords": ["carousel", "karuzel", "slajd", "slides"],
                "priority": "high",
                "description": "Generate a carousel deck (LinkedIn / Instagram).",
            },
            "write-linkedin-post": {
                "keywords": ["linkedin post", "post na linkedin", "napisz post", "zrob post"],
                "priority": "high",
                "description": "Draft a LinkedIn post in your voice.",
            },
            "write-newsletter": {
                "keywords": ["newsletter", "wydanie"],
                "priority": "medium",
                "description": "Compose a newsletter issue.",
            },
        },
    },
    "inbox-triage": {
        "label": "Inbox & communication (email triage, reply drafts)",
        "skills": {
            "inbox-triage": {
                "keywords": ["inbox", "poczt", "email", "mail"],
                "priority": "high",
                "description": "Morning email triage — important vs trash, calendar hits.",
            },
            "draft-reply": {
                "keywords": ["draft reply", "odpisz", "odpowiedz"],
                "priority": "medium",
                "description": "Draft a reply to an email thread.",
            },
        },
    },
    "scheduling": {
        "label": "Calendar & scheduling",
        "skills": {
            "schedule-meeting": {
                "keywords": ["schedule", "spotkani", "kalendarz", "calendar"],
                "priority": "medium",
                "description": "Create a calendar event via your calendar integration.",
            },
        },
    },
    "image-generation": {
        "label": "Image generation & editing",
        "skills": {
            "generate-image": {
                "keywords": ["generate image", "grafik", "obrazek", "thumbnail"],
                "priority": "medium",
                "description": "Text-to-image via your preferred generator.",
            },
        },
    },
    "dev-workflow": {
        "label": "Dev helpers (code review, test runners, debugging)",
        "skills": {
            "code-review": {
                "keywords": ["code review", "review", "przejrzyj kod"],
                "priority": "medium",
                "description": "Request a structured code review.",
            },
            "run-tests": {
                "keywords": ["run tests", "odpal test", "test suite"],
                "priority": "medium",
                "description": "Kick off your project test suite.",
            },
        },
    },
    "personal": {
        "label": "Personal (fitness, finance, habits — examples you can remove)",
        "skills": {
            "fitness-log": {
                "keywords": ["zjadl", "trening", "waga dzis", "fitness log"],
                "priority": "low",
                "description": "Log a meal / workout / weight entry.",
            },
        },
    },
}


def prompt_yes_no(question: str, default: bool = True) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        try:
            ans = input(question + suffix).strip().lower()
        except EOFError:
            return default
        if not ans:
            return default
        if ans in ("y", "yes", "t", "tak"):
            return True
        if ans in ("n", "no", "nie"):
            return False


def choose_categories() -> list[str]:
    print()
    print("Pick one or more categories (comma-separated numbers, e.g. 1,2,4):")
    print()
    keys = list(CATEGORIES.keys())
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {CATEGORIES[key]['label']}")
    print()

    while True:
        try:
            raw = input("Your choice: ").strip()
        except EOFError:
            print("\nAborted.")
            sys.exit(1)
        try:
            picks = [int(x.strip()) for x in raw.split(",") if x.strip()]
            chosen = [keys[p - 1] for p in picks if 1 <= p <= len(keys)]
        except (ValueError, IndexError):
            print("  Could not parse — try again, e.g. '1,3'")
            continue
        if not chosen:
            print("  Pick at least one category.")
            continue
        return chosen


def build_config(category_keys: list[str]) -> dict:
    skills: dict[str, dict] = {}
    for key in category_keys:
        for skill_name, skill_data in CATEGORIES[key]["skills"].items():
            skills[skill_name] = dict(skill_data)
    return {
        "version": "1.0",
        "description": "Generated by skill-router-config-init. Edit to match your actual skills & keywords.",
        "skills": skills,
    }


def main() -> int:
    print("skill-router — config init wizard")
    print("=" * 40)

    if CONFIG_PATH.exists():
        print(f"Config already exists at {CONFIG_PATH}")
        if not prompt_yes_no("Overwrite? A backup will be saved", default=False):
            print("Aborted.")
            return 1
        backup = CONFIG_PATH.with_suffix(
            f".json.bak-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        shutil.copy2(CONFIG_PATH, backup)
        print(f"Backup: {backup}")

    chosen = choose_categories()
    config = build_config(chosen)

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print(f"Wrote {CONFIG_PATH}")
    print(f"Skills seeded: {len(config['skills'])}")
    print()
    print("Next steps:")
    print(f"  1. Review & tune keywords:  $EDITOR {CONFIG_PATH}")
    print("  2. Tail the log to see matches in real time:")
    print("       tail -f ~/.claude/hooks/skill-router.log")
    print("  3. After a day of use, check stats:")
    print("       python3 skill-router-stats.py --days 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
