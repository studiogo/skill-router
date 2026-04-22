#!/usr/bin/env bash
# skill-router installer — kopiuje hook + skrypty do ~/.claude,
# rejestruje UserPromptSubmit w ~/.claude/settings.json idempotentnie.
# Uruchamiany z lokalnej kopii (./install.sh) albo przez curl | bash.
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

# 1. Preflight — potrzebujemy python3 do edycji JSON
command -v python3 >/dev/null 2>&1 || die "Nie znalazłem python3 w PATH. Zainstaluj Pythona 3.7+ i spróbuj jeszcze raz."

# 2. Ustal czy uruchamiamy z lokalnej kopii czy przez curl
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd -P || echo "")"
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/skill-router.py" ]]; then
  MODE="local"
  say "Tryb lokalny (z katalogu: $SCRIPT_DIR)"
else
  MODE="remote"
  say "Tryb zdalny — pobieram pliki z $REPO_BASE_URL"
  command -v curl >/dev/null 2>&1 || die "Nie znalazłem curl w PATH."
fi

# 3. Kopiowanie plików do ~/.claude/hooks/
mkdir -p "$HOOKS_DIR"
for f in "${FILES[@]}"; do
  target="$HOOKS_DIR/$f"
  if [[ "$MODE" == "local" ]]; then
    cp "$SCRIPT_DIR/$f" "$target"
  else
    curl -fsSL "$REPO_BASE_URL/$f" -o "$target"
  fi
  chmod +x "$target"
  say "zainstalowano $target"
done

# 4. Startowa konfiguracja tylko jeśli użytkownik nie ma jeszcze własnej
if [[ -f "$CONFIG" ]]; then
  say "zachowuję istniejący $CONFIG (bez nadpisywania)"
else
  if [[ "$MODE" == "local" ]]; then
    cp "$SCRIPT_DIR/$EXAMPLE_CONFIG" "$CONFIG"
  else
    curl -fsSL "$REPO_BASE_URL/$EXAMPLE_CONFIG" -o "$CONFIG"
  fi
  say "utworzono $CONFIG ze startowego szablonu"
fi

# 5. Rejestracja hooka w settings.json (idempotentnie)
if [[ -f "$SETTINGS" ]]; then
  BACKUP="$SETTINGS.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$SETTINGS" "$BACKUP"
  say "kopia zapasowa settings.json: $BACKUP"
else
  echo '{}' > "$SETTINGS"
  say "utworzono nowy settings.json"
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
    print("· skill-router jest już zarejestrowany w UserPromptSubmit — pomijam")
else:
    ups.append({
        "matcher": "",
        "hooks": [{"type": "command", "command": hook_cmd}],
    })
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("· zarejestrowano hook skill-router w UserPromptSubmit")
PY

# 6. Instrukcje końcowe
cat <<EOF

✅ skill-router zainstalowany.

Co dalej:
  1. (opcjonalnie) Interaktywny kreator konfiguracji:
       python3 $HOOKS_DIR/skill-router-config-init.py
  2. Otwórz nową sesję Claude Code, wpisz coś ze słowem kluczowym
     z $CONFIG — zobaczysz przypomnienie o skillu.
  3. Podgląd logu na żywo w drugim terminalu:
       tail -f $HOOKS_DIR/skill-router.log
  4. Po dniu używania — statystyki:
       python3 $HOOKS_DIR/skill-router-stats.py --days 1

Dokumentacja: https://github.com/studiogo/skill-router
EOF
