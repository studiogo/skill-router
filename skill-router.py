#!/usr/bin/env python3
"""
skill-router — Claude Code UserPromptSubmit hook (v0.2).

Reads prompt from stdin (JSON from Claude Code), emits two kinds of hints
back into Claude's context before it responds:

  1. 🎯 SKILL ACTIVATION — keyword-matched skills from ~/.claude/skill-rules.json
     (matches substrings of keywords you defined in the config)

  2. 📋 CONTEXT RULES — BM25-ranked feedback rules from memory/feedback_*.md
     (new in v0.2 — uses a Best Matching 25 implementation in stdlib so the
     most relevant historical lessons get injected automatically)

Philosophy:
  - SUGGEST only: never blocks prompt, exit 0 always, silent fail on errors.
  - Slavic-aware: normalizes Polish diacritics so "zrób karuzelę" matches "zrob karuzele".
  - Zero-deps: Python 3.7+ stdlib only (json, math, re, collections, pathlib). No pip install.
  - Observable: every invocation logged (append-only, auto-rotated at 1 MB).
"""
import datetime
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

# ─── Paths & constants ────────────────────────────────────────────────────────
CLAUDE_DIR = Path.home() / ".claude"
CONFIG_PATH = CLAUDE_DIR / "skill-rules.json"
LOG_PATH = CLAUDE_DIR / "hooks" / "skill-router.log"
LOG_MAX_BYTES = 1_000_000  # rotate after 1 MB

# Skill activation
MAX_SUGGESTIONS = 3
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
VALID_PRIORITIES = set(PRIORITY_ORDER.keys())

# Context rules (v0.2 BM25 feedback ranking)
CONTEXT_TOP_N = 3
CONTEXT_MIN_SCORE = 3.0           # below this, the match is weak — skip
CONTEXT_MIN_QUERY_TOKENS = 2      # don't rank if query has < N meaningful tokens
CONTEXT_MIN_DOC_HITS = 2          # doc must contain ≥N different query terms
CONTEXT_MAX_CORPUS = 500          # safety cap on indexed docs
DESC_BOOST = 3.0                  # multiplier for terms found in description/name

# Priority multipliers for BM25 final score. Docs marked `priority: critical`
# in their YAML frontmatter (e.g. Firewall Practima, pricing rules, safety)
# get a 10x boost so they practically never fall out of the top 3. Everything
# without an explicit priority defaults to `medium` (1×).
PRIORITY_BOOST = {
    "critical": 10.0,
    "high": 3.0,
    "medium": 1.0,
    "low": 0.3,
}
BM25_K1 = 1.5
BM25_B = 0.75
TOKEN_RE = re.compile(r"[a-z0-9]+")

# Polish diacritic → ASCII mapping
DIACRITIC_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    "Ą": "a", "Ć": "c", "Ę": "e", "Ł": "l", "Ń": "n",
    "Ó": "o", "Ś": "s", "Ź": "z", "Ż": "z",
})

# Common Polish/English stopwords — filtered from queries so trivial words
# don't skew BM25 scores. Not exhaustive but good enough for this scale.
STOPWORDS = {
    "a", "i", "o", "u", "w", "z", "za", "do", "na", "po", "od", "bez",
    "jest", "to", "ten", "ta", "te", "tak", "nie", "tez", "tylko", "albo",
    "lub", "czy", "jak", "co", "cos", "ktos", "jesli", "gdy", "ale",
    "the", "a", "an", "is", "are", "was", "were", "be", "of", "to",
    "in", "on", "for", "and", "or", "but", "if", "as", "at", "by", "it",
}


def normalize(text: str) -> str:
    """Lowercase + strip Polish diacritics. Idempotent for ASCII input."""
    return text.lower().translate(DIACRITIC_MAP)


# Rough Polish suffix stripper for BM25 matching. Not linguistically accurate
# — just enough to fold common inflections ("waga"/"wagę", "post"/"posty",
# "firewall"/"firewalla") to a shared stem so queries match their stored form.
# Longer suffixes first so they beat shorter prefixes of themselves.
_POLISH_SUFFIXES = (
    "iami", "ami", "owie", "owi", "ego", "emu", "iej", "ich", "imi",
    "ach", "om", "ow", "em", "ym", "im", "ia", "ie", "iu", "ki",
    "ka", "ko", "ku", "cy", "cie",
    "a", "e", "i", "o", "u", "y",
)


def stem(token: str) -> str:
    """Strip common Polish inflection endings. Leaves short tokens alone."""
    if len(token) <= 3:
        return token
    for end in _POLISH_SUFFIXES:
        if token.endswith(end) and len(token) - len(end) >= 3:
            return token[: -len(end)]
    return token


def tokenize(text: str) -> list:
    """Extract alphanumeric tokens after normalization and light stemming."""
    return [stem(t) for t in TOKEN_RE.findall(normalize(text))]


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
        pass  # logging is best-effort


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


# ─── BM25 context-rules ranking (v0.2) ────────────────────────────────────────

def _parse_frontmatter(content: str) -> dict:
    """Extract simple YAML frontmatter fields (description, priority, ...).
    Returns empty dict if no frontmatter. Does not support nested structures —
    only top-level `key: value` scalar lines."""
    out = {}
    if not content.startswith("---"):
        return out
    end = content.find("\n---", 3)
    if end < 0:
        return out
    for line in content[3:end].splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _parse_frontmatter_description(content: str) -> str:
    """Backwards-compatible wrapper — returns just the `description` field."""
    return _parse_frontmatter(content).get("description", "")


def load_feedback_corpus() -> list:
    """Scan all context rule files under ~/.claude/projects/*/memory/:
      - feedback_*.md (post-hoc lessons)
      - rules/*.md     (work-mode rules: core, tools, research, content, …)

    Deduplicates by filename (Syncthing / multiple project dirs can surface
    the same file more than once). Returns list of {name, description,
    priority, tokens, desc_tokens} dicts. Empty if none found.

    `desc_tokens` is a set built from the filename + frontmatter description —
    used to boost docs whose high-signal fields match the query."""
    corpus = []
    seen_names: set = set()
    base = CLAUDE_DIR / "projects"
    if not base.exists():
        return corpus
    # Both glob patterns combined — rules/*.md has higher signal density,
    # but feedback_*.md is the larger corpus.
    paths = list(base.glob("*/memory/feedback_*.md")) + list(base.glob("*/memory/rules/*.md"))
    for path in paths:
        if path.name in seen_names:
            continue
        if len(corpus) >= CONTEXT_MAX_CORPUS:
            break
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        seen_names.add(path.name)
        fm = _parse_frontmatter(content)
        description = fm.get("description", "")
        priority = fm.get("priority", "medium").lower()
        if priority not in PRIORITY_BOOST:
            priority = "medium"
        desc_tokens = set(tokenize(path.name + " " + description))
        corpus.append({
            "name": path.name,
            "description": description,
            "priority": priority,
            "tokens": tokenize(content),
            "desc_tokens": desc_tokens,
        })
    return corpus


def bm25_rank(query_tokens: list, corpus: list, top_n: int = CONTEXT_TOP_N) -> list:
    """Rank corpus against query using BM25 Okapi. Return top N above threshold.

    Formula (Okapi BM25, Robertson et al.):
        score(D, Q) = Σ IDF(qi) × [f(qi,D) × (k1+1)] / [f(qi,D) + k1 × (1 - b + b × |D|/avgdl)]
        IDF(qi)    = ln((N - df(qi) + 0.5) / (df(qi) + 0.5) + 1)
    """
    query = [t for t in query_tokens if t not in STOPWORDS and len(t) >= 3]
    if len(query) < CONTEXT_MIN_QUERY_TOKENS or not corpus:
        return []

    N = len(corpus)
    avgdl = sum(len(d["tokens"]) for d in corpus) / N
    if avgdl == 0:
        return []

    # Precompute doc frequencies for query terms
    df = {t: 0 for t in set(query)}
    for doc in corpus:
        doc_set = set(doc["tokens"])
        for t in df:
            if t in doc_set:
                df[t] += 1

    results = []
    for doc in corpus:
        tf = Counter(doc["tokens"])
        doc_len = len(doc["tokens"]) or 1
        score = 0.0
        unique_hits = 0
        for t in query:
            if df[t] == 0 or t not in tf:
                continue
            unique_hits += 1
            idf = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
            freq = tf[t]
            numerator = freq * (BM25_K1 + 1)
            denominator = freq + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / avgdl)
            if denominator > 0:
                term_score = idf * (numerator / denominator)
                # Boost terms that match filename or description (high-signal fields)
                if t in doc["desc_tokens"]:
                    term_score *= DESC_BOOST
                score += term_score
        # Require at least N different query terms to appear — prevents single
        # incidental word from scoring high in unrelated docs.
        if unique_hits < CONTEXT_MIN_DOC_HITS:
            continue
        # Apply priority multiplier (critical × 10, high × 3, medium × 1, low × 0.3).
        # Threshold is checked against the RAW score so that `low` priority docs
        # don't sneak in with tiny absolute scores, but a `critical` with
        # moderate raw relevance will beat a `medium` with equal raw relevance.
        if score >= CONTEXT_MIN_SCORE:
            boosted = score * PRIORITY_BOOST.get(doc["priority"], 1.0)
            results.append((boosted, doc))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_n]


def format_context_rules(ranked: list) -> str:
    """Format BM25-ranked feedback docs into a readable CONTEXT RULES block."""
    if not ranked:
        return ""
    lines = ["📋 CONTEXT RULES (relevant memory):"]
    for _score, doc in ranked:
        label = doc["description"] or doc["name"].replace(".md", "").replace("_", " ")
        # Trim long descriptions to keep context tidy
        if len(label) > 160:
            label = label[:157] + "..."
        lines.append(f"  → {doc['name']}: {label}")
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Read stdin
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

    prompt_norm = normalize(prompt_raw)

    # 2. Load skill-rules config (silent skip if missing/broken)
    matches = []
    if CONFIG_PATH.exists():
        try:
            rules = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            skills = rules.get("skills", {})
            if isinstance(skills, dict):
                for skill_name, skill_data in skills.items():
                    err = validate_skill(skill_name, skill_data)
                    if err:
                        log(f"CONFIG WARN: {err}")
                        continue
                    for keyword in skill_data["keywords"]:
                        if normalize(keyword) in prompt_norm:
                            matches.append({
                                "skill": skill_name,
                                "keyword": keyword,
                                "priority": skill_data.get("priority", "medium"),
                            })
                            break
        except Exception as e:
            log(f"ERROR: config not valid JSON ({e})")

    # 3. Rank feedback rules (v0.2 — BM25)
    ranked_rules = []
    try:
        corpus = load_feedback_corpus()
        if corpus:
            ranked_rules = bm25_rank(tokenize(prompt_raw), corpus)
    except Exception as e:
        log(f"BM25 ERROR (non-fatal): {e}")

    # 4. If nothing matched — silent exit
    if not matches and not ranked_rules:
        log(f"NO MATCH | prompt={prompt_raw[:80]!r}")
        sys.exit(0)

    # 5. Build output — two sections
    sections = []

    if matches:
        matches.sort(key=lambda m: PRIORITY_ORDER[m["priority"]])
        top_skills = matches[:MAX_SUGGESTIONS]
        names = ", ".join(f"`{m['skill']}`" for m in top_skills)
        sections.append(f"🎯 SKILL ACTIVATION: Rozważ użycie skilla {names}")

    if ranked_rules:
        sections.append(format_context_rules(ranked_rules))

    output = "\n\n".join(sections)
    print(output)

    # Compact log line: skills + top feedback names
    skill_str = ",".join(m["skill"] for m in matches[:MAX_SUGGESTIONS]) or "-"
    rule_str = ",".join(d["name"] for _, d in ranked_rules) or "-"
    log(f"MATCH | prompt={prompt_raw[:80]!r} | skills={skill_str} | rules={rule_str}")
    sys.exit(0)


if __name__ == "__main__":
    main()
