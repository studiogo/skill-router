#!/usr/bin/env python3
"""Regenerate ~/.claude/skill-rules.json from ~/.claude/skills/*/SKILL.md.

Each skill's `description:` in its YAML frontmatter typically contains quoted
trigger phrases ("napisz post", "zrób X"). We extract all of them, add the
skill's own name (split on hyphens) as a fallback keyword, and write a fresh
skill-rules.json. Existing priorities are preserved.

Run after installing a new skill or editing a SKILL.md description:
    python3 scripts/gen-skill-rules.py
"""
import datetime
import json
import re
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"
CONFIG_PATH = Path.home() / ".claude" / "skill-rules.json"


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm: dict = {}
    current_key = None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if value.startswith('"') and value.endswith('"') and len(value) > 1:
                fm[key] = value[1:-1]
                current_key = None
            elif value.startswith('"') and not value.endswith('"'):
                fm[key] = value[1:]
                current_key = key
            else:
                fm[key] = value.strip('"').strip("'")
                current_key = None
        elif current_key:
            clean = line.strip()
            if clean.endswith('"'):
                fm[current_key] += " " + clean[:-1]
                current_key = None
            else:
                fm[current_key] += " " + clean
    return fm


def extract_keywords(description: str, skill_name: str) -> list:
    """Pull quoted phrases + skill-name words as BM25 seed keywords.

    Supports three quote styles: ASCII double ("foo"), Polish typographic (
    „foo"), and ASCII single ('foo'). Single quotes are only matched when
    both delimiters look like phrase boundaries (preceded/followed by space,
    punctuation, or string edge) so apostrophes in possessives/contractions
    like Pocock'a or deadline'y don't leak in as fake triggers.
    """
    kws: set = set()
    for pattern in [r'"([^"]+?)"', r'„([^"]+?)"']:
        for m in re.finditer(pattern, description):
            phrase = m.group(1).strip().lower()
            if len(phrase) >= 3:
                kws.add(phrase)
    single_boundary = r"(?:(?<=^)|(?<=[\s,.;:—\-(\[]))'([^']+?)'(?=[\s,.;:!?—\-)\]]|$)"
    for m in re.finditer(single_boundary, description):
        phrase = m.group(1).strip().lower()
        if len(phrase) >= 3:
            kws.add(phrase)
    base = skill_name.replace("-", " ").replace("_", " ").lower()
    kws.add(base)
    for word in base.split():
        if len(word) >= 4:
            kws.add(word)
    return sorted(kws)


def main() -> None:
    # Preserve existing priorities
    existing = {}
    if CONFIG_PATH.exists():
        try:
            existing = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("skills", {})
        except Exception:
            pass
        backup = CONFIG_PATH.with_suffix(
            f".json.bak-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        backup.write_text(CONFIG_PATH.read_text(), encoding="utf-8")
        print(f"Kopia zapasowa: {backup}")

    skills: dict = {}
    processed, skipped = 0, []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            skipped.append(f"{skill_dir.name} (brak SKILL.md)")
            continue
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            skipped.append(f"{skill_dir.name} (read error)")
            continue

        fm = parse_frontmatter(text)
        name = fm.get("name", skill_dir.name)
        description = fm.get("description", "")
        keywords = extract_keywords(description, name)
        if not keywords:
            skipped.append(f"{skill_dir.name} (brak keywordów)")
            continue

        priority = existing.get(name, {}).get("priority", "medium")
        skills[name] = {"keywords": keywords, "priority": priority}
        processed += 1

    out = {
        "version": "1.1",
        "description": "Auto-generated przez scripts/gen-skill-rules.py z SKILL.md frontmatter. Ręczne edycje zostaną nadpisane — edytuj SKILL.md zamiast tego.",
        "skills": skills,
    }
    CONFIG_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Zapisano: {CONFIG_PATH}")
    print(f"Przetworzone: {processed} skille")
    print(f"Pominięte: {len(skipped)}")
    for s in skipped:
        print(f"  - {s}")


if __name__ == "__main__":
    main()
