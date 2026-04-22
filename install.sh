#!/usr/bin/env bash
# skill-router installer — copies hook + scripts to ~/.claude,
# registers UserPromptSubmit in ~/.claude/settings.json idempotently.
# Run either from a local clone (./install.sh) or via curl | bash.
set -euo pipefail

REPO_BASE_URL="https://raw.githubusercontent.com/studiogo/skill-router/main"
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS="$CLAUDE_DIR/settings.json"
CONFIG="$CLAUDE_DIR/skill-rules.json"

FILES=(
  "skill-router.py"
  "skill-router-stats.py"
  "skill-router-config-init.py"
)

EXAMPLE_CONFIG="skill-rules.example.json"

say()  { printf "\033[1;34m▸\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; exit 1; }

# 1. Preflight ─ we need python3 + a way to edit JSON
command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH. Install Python 3.7+ and rerun."

# 2. Figure out whether we run from a local clone or remote
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd -P || echo "")"
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/skill-router.py" ]]; then
  MODE="local"
  say "Running from local clone: $SCRIPT_DIR"
else
  MODE="remote"
  say "Running in remote mode — fetching from $REPO_BASE_URL"
  command -v curl >/dev/null 2>&1 || die "curl not found on PATH."
fi

# 3. Copy files into ~/.claude/hooks/
mkdir -p "$HOOKS_DIR"
for f in "${FILES[@]}"; do
  target="$HOOKS_DIR/$f"
  if [[ "$MODE" == "local" ]]; then
    cp "$SCRIPT_DIR/$f" "$target"
  else
    curl -fsSL "$REPO_BASE_URL/$f" -o "$target"
  fi
  chmod +x "$target"
  say "installed $target"
done

# 4. Seed skill-rules.json only if user has none
if [[ -f "$CONFIG" ]]; then
  say "keeping existing $CONFIG (no overwrite)"
else
  if [[ "$MODE" == "local" ]]; then
    cp "$SCRIPT_DIR/$EXAMPLE_CONFIG" "$CONFIG"
  else
    curl -fsSL "$REPO_BASE_URL/$EXAMPLE_CONFIG" -o "$CONFIG"
  fi
  say "created $CONFIG from example template"
fi

# 5. Register hook in settings.json idempotently
if [[ -f "$SETTINGS" ]]; then
  BACKUP="$SETTINGS.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$SETTINGS" "$BACKUP"
  say "settings.json backed up to $BACKUP"
else
  echo '{}' > "$SETTINGS"
  say "created new settings.json"
fi

python3 - <<PY
import json, pathlib, sys

path = pathlib.Path("$SETTINGS")
data = json.loads(path.read_text() or "{}")

hook_cmd = "python3 \$HOME/.claude/hooks/skill-router.py"
hooks = data.setdefault("hooks", {})
ups = hooks.setdefault("UserPromptSubmit", [])

def already_registered(blocks):
    for block in blocks:
        for h in block.get("hooks", []):
            if h.get("type") == "command" and "skill-router.py" in (h.get("command") or ""):
                return True
    return False

if already_registered(ups):
    print("· skill-router already registered in UserPromptSubmit — skipping")
else:
    ups.append({
        "matcher": "",
        "hooks": [{"type": "command", "command": hook_cmd}],
    })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("· registered skill-router hook in UserPromptSubmit")
PY

# 6. Final instructions
cat <<EOF

✅ skill-router installed.

Next steps:
  1. (optional) Interactive wizard to seed keywords:
       python3 $HOOKS_DIR/skill-router-config-init.py
  2. Open a new Claude Code session, type something with a keyword
     from $CONFIG, and watch the reminder appear.
  3. Tail the log in a second terminal:
       tail -f $HOOKS_DIR/skill-router.log
  4. After a day of use:
       python3 $HOOKS_DIR/skill-router-stats.py --days 1

Docs: https://github.com/studiogo/skill-router
EOF
