# skill-router

**Automatyczne przypomnienia o Twoich skillach w Claude Code.** Claude zapomina o kartkach procedur po długiej sesji. `skill-router` to drugi asystent — czyta każdy Twój prompt, porównuje z mapą słów kluczowych i szepcze Claude'owi: *„sprawdź kartkę 13"*.

Jeden hook w Pythonie, zero zależności (`pip install` nie jest potrzebny).

---

## Co robi

1. **Słucha każdego promptu** (hook `UserPromptSubmit`) i normalizuje polskie diakrytyki — `„zrób karuzelę"` matchuje keyword `„zrob karuzele"`.
2. **Sugeruje do 3 skilli** gdy trafi na słowo kluczowe z Twojego configu. Tryb SUGGEST — nigdy nie blokuje promptu.
3. **Loguje każde uruchomienie** do `~/.claude/hooks/skill-router.log` (auto-rotacja po 1 MB), żeby potem dało się policzyć co matchuje, a co jest martwe.

## Przykład

```
$ echo '{"prompt":"Zrób karuzelę na LinkedIn"}' | python3 skill-router.py
🎯 SKILL ACTIVATION: Rozważ użycie skilla `create-carousel`
```

Claude widzi to w kontekście przed odpowiedzią, więc *faktycznie* odpala skill zamiast rozwiązywać od zera.

---

## Instalacja

### Opcja A — one-liner (zalecana)

```bash
curl -fsSL https://raw.githubusercontent.com/studiogo/skill-router/main/install.sh | bash
```

Kopiuje `skill-router.py` + dwie skryptowe komendy do `~/.claude/hooks/`, podpina hook w `~/.claude/settings.json` (z automatycznym backupem), stawia startowy `skill-rules.example.json`. Nie nadpisze istniejącej konfiguracji.

### Opcja B — manualnie

```bash
git clone https://github.com/studiogo/skill-router.git
cd skill-router
./install.sh
```

Albo jeszcze bardziej ręcznie — skopiuj `skill-router.py` do `~/.claude/hooks/`, `skill-rules.example.json` do `~/.claude/skill-rules.json`, i dopisz do `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "python3 $HOME/.claude/hooks/skill-router.py"
      }]
    }]
  }
}
```

## Konfiguracja

### Pierwszy config przez wizarda

```bash
python3 skill-router-config-init.py
```

Pyta o kategorie (content, inbox, scheduling, image-gen, dev, personal) i generuje startowy `~/.claude/skill-rules.json`. Backup starego configu zawsze przed nadpisaniem.

### Ręczna edycja

```json
{
  "version": "1.0",
  "skills": {
    "create-carousel": {
      "keywords": ["carousel", "karuzela", "slajdy"],
      "priority": "high"
    }
  }
}
```

- `priority`: `"high"` | `"medium"` | `"low"` — sugestie sortowane w tej kolejności
- `keywords`: lista stringów (lowercase), matching po substringu + normalizacji diakrytyków
- Niepoprawne wpisy (zła priority, keywords nie-lista) są pomijane i logowane jako `CONFIG WARN`

> **Tip: używaj rdzeni słów, nie form gramatycznych.** Matching jest substring, więc `"karuzel"` łapie *karuzela / karuzelę / karuzeli / karuzele*. `"spotkani"` łapie *spotkanie / spotkania / spotkaniu*. Jedna forma bazowa = pełna odmiana po polsku.

---

## Komendy

### Podgląd loga na żywo

```bash
tail -f ~/.claude/hooks/skill-router.log
```

Każda linia to: timestamp + typ (`MATCH` / `NO MATCH` / `SKIP` / `ERROR`) + prompt (obcinany do 80 znaków).

### Statystyki użycia

```bash
python3 skill-router-stats.py                 # all time
python3 skill-router-stats.py --days 7        # ostatni tydzień
python3 skill-router-stats.py --skill inbox   # drill-down na jeden skill
```

Pokazuje: total/matches/no-match, match rate %, top 10 skilli, **martwe skille** (skonfigurowane, ale żadnego matcha) — świetny sygnał że keyword trzeba przepisać albo skill usunąć.

---

## Jak to działa

```
prompt użytkownika
    ↓
Claude Code → UserPromptSubmit hook → skill-router.py
    ↓
normalize(prompt)  ← lowercase + ą→a, ę→e, ł→l, ń→n, ó→o, ś→s, ź→z, ż→z, ć→c
    ↓
dla każdego skilla w skill-rules.json:
    jeśli normalize(keyword) jest w znormalizowanym promptcie → match
    ↓
sortuj po priority (high > medium > low), weź top 3
    ↓
wypluj na stdout: "🎯 SKILL ACTIVATION: Rozważ użycie skilla `name1`, `name2`"
    ↓
Claude widzi reminder w kontekście przed odpowiedzią
```

**Silent fail** wszędzie — brak configa, broken JSON, prompt 50 KB, sigma Unicode — hook nigdy nie ubija promptu.

---

## Troubleshooting

| Objaw | Diagnoza |
|---|---|
| `tail -f` pokazuje same `NO MATCH` | Keywordy w twoim configu nie pasują do tego jak faktycznie mówisz. Odpal `skill-router-stats.py --days 7` → sekcja „zero matches" powie które skille są martwe. |
| `CONFIG WARN` w logu | Zły format `skill-rules.json`. Komunikat mówi co poprawić (priority, keywords, typ entry). |
| Hook nie odpala się w ogóle | Sprawdź `~/.claude/settings.json` — czy jest blok `UserPromptSubmit`? Sprawdź `which python3`. |
| Log rośnie w nieskończoność | Hook sam rotuje po 1 MB (`.log.1`). Jeśli nadal duży — `LOG_MAX_BYTES` w `skill-router.py` obniż. |

---

## Inspiracja i kredyty

Ten projekt powstał po przeczytaniu postu **[„Claude Code is a Beast" autorstwa u/JokeGold5455](https://www.reddit.com/r/ClaudeAI/comments/1oivjvm/claude_code_is_a_beast_tips_from_6_months_of/)** i jego repo [`diet103/claude-code-infrastructure-showcase`](https://github.com/diet103/claude-code-infrastructure-showcase) (MIT). Koncept przechwytywania `UserPromptSubmit` + plik `skill-rules.json` zapożyczone stamtąd (uczciwie — pomysł nie jest nasz).

Czym się różnimy:

|  | u/JokeGold5455 | skill-router (ten projekt) |
|---|---|---|
| Język hooka | TypeScript + Bash (wymaga `npx tsx`, Node, npm) | Python 3 (stdlib only, zero deps) |
| Matching | keywords + **regex intent patterns** + 4 poziomy priorytetu | keywords + **polska normalizacja diakrytyków**, 3 poziomy |
| Enforcement | `block` / `suggest` / `warn` | **tylko SUGGEST**, nigdy nie blokuje |
| Error handling | `stderr` + `exit 1` przy błędzie | silent fail, `exit 0` zawsze |
| Logowanie | brak | auto-rotacja, CLI stats + dead-keyword detection |
| Onboarding nowego usera | ręczna edycja JSON | interaktywny wizard (`config-init`) |
| Docelowa grupa | developer z dużym repo TypeScript | **solopreneur polskojęzyczny** używający Claude Code do contentu/maila/planowania |

Jego system jest mocniejszy dla programistycznych workflowów z Stop-hook i build-resolverem. Nasz jest prostszy w instalacji i rozumie, że „zrób karuzelę" i „zrob karuzele" to to samo.

## Licencja

MIT — patrz [LICENSE](LICENSE).
