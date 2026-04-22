#!/usr/bin/env python3
"""
skill-router — Claude Code UserPromptSubmit hook.

Reads prompt from stdin (JSON from Claude Code), matches keywords against
~/.claude/skill-rules.json, prints a reminder to stdout when a skill matches.

Philosophy:
  - SUGGEST only: never blocks prompt, exit 0 always, silent fail on errors.
  - Slavic-aware: normalizes Polish diacritics so "zrób karuzelę" matches "zrob karuzele".
  - Observable: every invocation is logged (append-only, auto-rotated at 1 MB).

Dependencies: Python 3.7+ stdlib only (json, sys, datetime, pathlib). No pip install.
"""
import json
import sys
import datetime
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "skill-rules.json"
LOG_PATH = Path.home() / ".claude" / "hooks" / "skill-router.log"
LOG_MAX_BYTES = 1_000_000  # rotate after 1 MB
MAX_SUGGESTIONS = 3
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
VALID_PRIORITIES = set(PRIORITY_ORDER.keys())

# Polish diacritic → ASCII mapping. Makes matching case- and accent-insensitive.
# "Zrób KARUZELĘ" and "zrob karuzele" both normalize to "zrob karuzele".
DIACRITIC_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    "Ą": "a", "Ć": "c", "Ę": "e", "Ł": "l", "Ń": "n",
    "Ó": "o", "Ś": "s", "Ź": "z", "Ż": "z",
})


def normalize(text: str) -> str:
    """Lowercase + strip Polish diacritics. Idempotent for ASCII input."""
    return text.lower().translate(DIACRITIC_MAP)


def log(msg: str) -> None:
    """Append log line. Rotate file when it crosses LOG_MAX_BYTES."""
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > LOG_MAX_BYTES:
            backup = LOG_PATH.with_suffix(".log.1")
            if backup.exists():
                backup.unlink()
            LOG_PATH.rename(backup)
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass  # logging is best-effort; never block the hook


def validate_skill(name: str, data: dict) -> str | None:
    """Return error message if skill entry is malformed, else None."""
    if not isinstance(data, dict):
        return f"skill {name!r}: entry must be an object"
    keywords = data.get("keywords")
    if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
        return f"skill {name!r}: 'keywords' must be a list of strings"
    priority = data.get("priority", "medium")
    if priority not in VALID_PRIORITIES:
        return f"skill {name!r}: 'priority' must be one of {sorted(VALID_PRIORITIES)}, got {priority!r}"
    return None


def main() -> None:
    # 1. Read stdin (Claude Code sends a JSON envelope).
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        prompt_raw = data.get("prompt") or ""
    except Exception:
        log("ERROR: could not parse stdin")
        sys.exit(0)

    if not prompt_raw:
        log("SKIP: empty prompt")
        sys.exit(0)

    prompt = normalize(prompt_raw)

    # 2. Load config (silent skip if missing / broken — never break the user's workflow).
    if not CONFIG_PATH.exists():
        sys.exit(0)
    try:
        rules = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"ERROR: config not valid JSON ({e})")
        sys.exit(0)

    skills = rules.get("skills", {})
    if not isinstance(skills, dict) or not skills:
        sys.exit(0)

    # 3. Match keywords. Invalid entries are skipped with a log line.
    matches = []
    for skill_name, skill_data in skills.items():
        err = validate_skill(skill_name, skill_data)
        if err:
            log(f"CONFIG WARN: {err}")
            continue
        for keyword in skill_data["keywords"]:
            if normalize(keyword) in prompt:
                matches.append({
                    "skill": skill_name,
                    "keyword": keyword,
                    "priority": skill_data.get("priority", "medium"),
                })
                break  # one match per skill is enough

    if not matches:
        log(f"NO MATCH | prompt={prompt_raw[:80]!r}")
        sys.exit(0)

    # 4. Sort by priority, take top N.
    matches.sort(key=lambda m: PRIORITY_ORDER[m["priority"]])
    top = matches[:MAX_SUGGESTIONS]

    # 5. Emit reminder (goes into Claude's prompt context).
    names = ", ".join(f"`{m['skill']}`" for m in top)
    output = f"🎯 SKILL ACTIVATION: Rozważ użycie skilla {names}"
    print(output)
    log(f"MATCH | prompt={prompt_raw[:80]!r} | output={output}")
    sys.exit(0)


if __name__ == "__main__":
    main()
