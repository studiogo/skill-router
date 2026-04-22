#!/usr/bin/env python3
"""
skill-router-stats — analizator logu skill-routera.

Czyta ~/.claude/hooks/skill-router.log i pokazuje:
  - łączną liczbę uruchomień
  - match rate (% promptów z co najmniej jednym skillem)
  - top N skilli wg liczby matchy
  - martwe skille (skonfigurowane, ale nigdy nie zmatchowane — kandydaci do poprawy)

Użycie:
  python3 skill-router-stats.py                 # cały czas
  python3 skill-router-stats.py --days 7        # ostatnie 7 dni
  python3 skill-router-stats.py --skill inbox   # jeden konkretny skill
"""
import argparse
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

LOG_PATH = Path.home() / ".claude" / "hooks" / "skill-router.log"
CONFIG_PATH = Path.home() / ".claude" / "skill-rules.json"

LINE_RE = re.compile(r"^\[(?P<ts>[0-9T:\-]+)\] (?P<kind>CONFIG WARN|NO MATCH|MATCH|SKIP|ERROR)\b[\s:|]*(?P<rest>.*)$")
MATCH_SKILLS_RE = re.compile(r"output=.*?Rozważ użycie skilla (?P<skills>.+)")
SKILL_NAME_RE = re.compile(r"`([^`]+)`")


def parse_log(path: Path, since: datetime.datetime | None):
    """Yield (timestamp, kind, rest) for each parseable log line."""
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = LINE_RE.match(line.rstrip("\n"))
            if not m:
                continue
            try:
                ts = datetime.datetime.fromisoformat(m.group("ts"))
            except ValueError:
                continue
            if since and ts < since:
                continue
            yield ts, m.group("kind"), m.group("rest")


def extract_skills(rest: str) -> list[str]:
    m = MATCH_SKILLS_RE.search(rest)
    if not m:
        return []
    return SKILL_NAME_RE.findall(m.group("skills"))


def load_configured_keywords() -> dict[str, list[str]]:
    """Return {skill_name: [keywords]} from skill-rules.json. Empty on any error."""
    try:
        rules = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        out = {}
        for name, data in rules.get("skills", {}).items():
            out[name] = list(data.get("keywords") or [])
        return out
    except Exception:
        return {}


def load_log_prompts(path: Path, since: datetime.datetime | None):
    """Yield normalized prompt text from every log line that contains one."""
    prompt_re = re.compile(r"prompt=(['\"])(?P<prompt>.*?)\1")
    for _, _, rest in parse_log(path, since):
        pm = prompt_re.search(rest)
        if pm:
            yield pm.group("prompt").lower()


def main() -> int:
    ap = argparse.ArgumentParser(description="Analiza skill-router.log")
    ap.add_argument("--days", type=int, default=None,
                    help="Licz tylko wpisy z ostatnich N dni")
    ap.add_argument("--skill", type=str, default=None,
                    help="Pokaż statystyki jednego konkretnego skilla")
    ap.add_argument("--top", type=int, default=10, help="Ilu najpopularniejszych skilli pokazać (domyślnie 10)")
    args = ap.parse_args()

    since = None
    if args.days:
        since = datetime.datetime.now() - datetime.timedelta(days=args.days)

    total = 0
    matches = 0
    no_match = 0
    errors = 0
    skill_counts: Counter = Counter()

    for _, kind, rest in parse_log(LOG_PATH, since):
        total += 1
        if kind == "MATCH":
            matches += 1
            for s in extract_skills(rest):
                skill_counts[s] += 1
        elif kind == "NO MATCH":
            no_match += 1
        elif kind in ("ERROR", "CONFIG WARN"):
            errors += 1

    if total == 0:
        print(f"Brak wpisów w logu: {LOG_PATH}", file=sys.stderr)
        return 1

    actionable = matches + no_match  # SKIP / ERROR nie liczą się do match rate
    rate = (matches / actionable * 100) if actionable else 0
    window = f"ostatnie {args.days} dni" if args.days else "cały czas"

    print(f"skill-router — statystyki ({window})")
    print(f"  log:             {LOG_PATH}")
    print(f"  łącznie wpisów:  {total}")
    print(f"  matche:          {matches}")
    print(f"  bez matcha:      {no_match}")
    print(f"  błędy/warningi:  {errors}")
    print(f"  match rate:      {rate:.1f}%")
    print()

    if args.skill:
        count = skill_counts.get(args.skill, 0)
        print(f"skill {args.skill!r}: {count} match(ów)")
        return 0

    if skill_counts:
        print(f"Top {args.top} skilli wg liczby matchy:")
        for name, cnt in skill_counts.most_common(args.top):
            bar = "█" * min(cnt, 40)
            print(f"  {name:<28} {cnt:>4}  {bar}")
        print()

    # Martwe skille — skonfigurowane, ale w tym oknie bez matcha
    configured = load_configured_keywords()
    if configured:
        dead_skills = [s for s in configured if s not in skill_counts]
        if dead_skills:
            print(f"Skille bez matcha w tym oknie ({len(dead_skills)}):")
            for s in sorted(dead_skills):
                print(f"  {s}")
            print("  → popraw słowa kluczowe albo usuń skill jeśli nieaktywny")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
