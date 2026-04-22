#!/usr/bin/env python3
"""
skill-router-config-init — interaktywny kreator, który generuje
startowy ~/.claude/skill-rules.json z gotowych szablonów kategorii.

Uruchom raz po instalacji, potem dostosuj ręcznie pod swój workflow.
"""
import datetime
import json
import shutil
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "skill-rules.json"

CATEGORIES: dict[str, dict] = {
    "content-creation": {
        "label": "Tworzenie treści (LinkedIn, karuzele, posty, newsletter)",
        "skills": {
            "create-carousel": {
                "keywords": ["carousel", "karuzel", "slajd", "slides"],
                "priority": "high",
                "description": "Generuj karuzelę slajdów (LinkedIn / Instagram).",
            },
            "write-linkedin-post": {
                "keywords": ["linkedin post", "post na linkedin", "napisz post", "zrob post"],
                "priority": "high",
                "description": "Napisz post na LinkedIn w Twoim tonie.",
            },
            "write-newsletter": {
                "keywords": ["newsletter", "wydanie"],
                "priority": "medium",
                "description": "Przygotuj wydanie newslettera.",
            },
        },
    },
    "inbox-triage": {
        "label": "Skrzynka i komunikacja (triage maili, drafty odpowiedzi)",
        "skills": {
            "inbox-triage": {
                "keywords": ["inbox", "poczt", "email", "mail"],
                "priority": "high",
                "description": "Poranny triage poczty — ważne vs śmieci, spotkania, drafty odpowiedzi.",
            },
            "draft-reply": {
                "keywords": ["draft reply", "odpisz", "odpowiedz"],
                "priority": "medium",
                "description": "Napisz szkic odpowiedzi na wątek mailowy.",
            },
        },
    },
    "scheduling": {
        "label": "Kalendarz i planowanie",
        "skills": {
            "schedule-meeting": {
                "keywords": ["schedule", "spotkani", "kalendarz", "calendar"],
                "priority": "medium",
                "description": "Utwórz wydarzenie w kalendarzu przez integrację.",
            },
        },
    },
    "image-generation": {
        "label": "Generowanie i edycja obrazów",
        "skills": {
            "generate-image": {
                "keywords": ["generate image", "grafik", "obrazek", "thumbnail"],
                "priority": "medium",
                "description": "Tekst → obraz przez Twojego preferowanego generatora.",
            },
        },
    },
    "dev-workflow": {
        "label": "Narzędzia dev (review kodu, odpalanie testów, debug)",
        "skills": {
            "code-review": {
                "keywords": ["code review", "review", "przejrzyj kod"],
                "priority": "medium",
                "description": "Zrób strukturalny review kodu.",
            },
            "run-tests": {
                "keywords": ["run tests", "odpal test", "test suite"],
                "priority": "medium",
                "description": "Uruchom suite testów projektu.",
            },
        },
    },
    "personal": {
        "label": "Prywatne (fitness, finanse, nawyki — przykłady do modyfikacji)",
        "skills": {
            "fitness-log": {
                "keywords": ["zjadl", "trening", "waga dzis", "fitness log"],
                "priority": "low",
                "description": "Zapisz wpis o posiłku / treningu / wadze.",
            },
        },
    },
}


def prompt_yes_no(question: str, default: bool = True) -> bool:
    suffix = " [T/n] " if default else " [t/N] "
    while True:
        try:
            ans = input(question + suffix).strip().lower()
        except EOFError:
            return default
        if not ans:
            return default
        if ans in ("t", "tak", "y", "yes"):
            return True
        if ans in ("n", "nie", "no"):
            return False


def choose_categories() -> list[str]:
    print()
    print("Wybierz jedną lub więcej kategorii (numery po przecinku, np. 1,2,4):")
    print()
    keys = list(CATEGORIES.keys())
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {CATEGORIES[key]['label']}")
    print()

    while True:
        try:
            raw = input("Twój wybór: ").strip()
        except EOFError:
            print("\nPrzerwano.")
            sys.exit(1)
        try:
            picks = [int(x.strip()) for x in raw.split(",") if x.strip()]
            chosen = [keys[p - 1] for p in picks if 1 <= p <= len(keys)]
        except (ValueError, IndexError):
            print("  Nie zrozumiałem — spróbuj ponownie, np. '1,3'")
            continue
        if not chosen:
            print("  Wybierz przynajmniej jedną kategorię.")
            continue
        return chosen


def build_config(category_keys: list[str]) -> dict:
    skills: dict[str, dict] = {}
    for key in category_keys:
        for skill_name, skill_data in CATEGORIES[key]["skills"].items():
            skills[skill_name] = dict(skill_data)
    return {
        "version": "1.0",
        "description": "Wygenerowane przez skill-router-config-init. Edytuj pod swoje realne skille i słowa kluczowe.",
        "skills": skills,
    }


def main() -> int:
    print("skill-router — kreator konfiguracji")
    print("=" * 40)

    if CONFIG_PATH.exists():
        print(f"Konfiguracja już istnieje: {CONFIG_PATH}")
        if not prompt_yes_no("Nadpisać? (zrobię kopię zapasową)", default=False):
            print("Przerwano.")
            return 1
        backup = CONFIG_PATH.with_suffix(
            f".json.bak-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        shutil.copy2(CONFIG_PATH, backup)
        print(f"Kopia zapasowa: {backup}")

    chosen = choose_categories()
    config = build_config(chosen)

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print(f"Zapisano: {CONFIG_PATH}")
    print(f"Liczba skilli na start: {len(config['skills'])}")
    print()
    print("Co dalej:")
    print(f"  1. Dostosuj słowa kluczowe:  $EDITOR {CONFIG_PATH}")
    print("  2. Podgląd logu na żywo:")
    print("       tail -f ~/.claude/hooks/skill-router.log")
    print("  3. Po dniu używania — statystyki:")
    print("       python3 skill-router-stats.py --days 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
