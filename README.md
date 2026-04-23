# skill-router

**Automatyczne przypomnienia o Twoich skillach w Claude Code + wstrzykiwanie relevantnych zasad z pamięci.** Claude zapomina o kartkach procedur po długiej sesji. `skill-router` to drugi asystent — czyta każdy Twój prompt i szepcze Claude'owi: *„sprawdź kartkę 13 — oraz zasady A, B, C z pamięci"*.

Jeden hook w Pythonie, zero zależności (`pip install` nie jest potrzebny).

---

## Co robi

1. **Słucha każdego promptu** (hook `UserPromptSubmit`) i normalizuje polskie diakrytyki — `„zrób karuzelę"` matchuje keyword `„zrob karuzele"`.
2. **Sugeruje do 3 skilli** gdy trafi na słowo kluczowe z Twojego configu. Tryb SUGGEST — nigdy nie blokuje promptu.
3. **(v0.2) Wstrzykuje do 3 zasad z `memory/feedback_*.md` + `memory/rules/*.md`** rankowanych przez **BM25** — algorytm używany przez Google/Elasticsearch. Dzięki temu Claude widzi relevantne zasady historyczne (np. „karuzele: używaj Style B Terminal Tech") zanim odpowie.
4. **(v0.3) Priority boost** — reguły oznaczone `priority: critical` w YAML frontmatter dostają 10× wzmocnienie w rankingu. Krytyczne zasady (Firewall umowy, cennik, nieodwracalne akcje) praktycznie nigdy nie wypadają z top 3.
5. **(v0.3) Auto-mapowanie skilli** — skrypt `scripts/gen-skill-rules.py` czyta `~/.claude/skills/*/SKILL.md` i generuje cały `skill-rules.json` z frontmatter'ów. Dodajesz nowy skill → jedna komenda i hook go rozpoznaje.
6. **Loguje każde uruchomienie** do `~/.claude/hooks/skill-router.log` (auto-rotacja po 1 MB), żeby potem dało się policzyć co matchuje, a co jest martwe.

## Przykład

```
$ echo '{"prompt":"Zrób karuzelę na LinkedIn o AI agentach"}' | python3 skill-router.py
🎯 SKILL ACTIVATION: Rozważ użycie skilla `create-carousel`

📋 CONTEXT RULES (relevant memory):
  → feedback_carousel_default_style_b.md: Style B jest domyślny dla nowych karuzel LinkedIn od 18.04...
  → feedback_carousel_linkedin_style.md: Jak pisać teksty do karuzel i postów LinkedIn...
  → feedback_linkedin_api.md: Nie publikować przez Postiz — używać LinkedIn API bezpośrednio...
```

Claude widzi to w kontekście przed odpowiedzią, więc *faktycznie* odpala skill zamiast rozwiązywać od zera, **i stosuje Twoje historyczne zasady bez pytania.**

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
python3 skill-router-stats.py                 # cały czas
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
┌───────────────────────────┬─────────────────────────────────────┐
│ A) SKILL ACTIVATION       │ B) CONTEXT RULES (v0.2)             │
│                           │                                     │
│ dla każdego skilla:       │ skanuj memory/feedback_*.md         │
│   substring match         │ tokenize + stemming polski          │
│   z keyword w configu     │ BM25 ranking (IDF × TF × length)    │
│ top 3 po priority         │ boost dla filename + description    │
│                           │ min 2 hits, min score 3.0           │
│                           │ top 3 > threshold                   │
└───────────────────────────┴─────────────────────────────────────┘
    ↓
output (2 sekcje):
  🎯 SKILL ACTIVATION: Rozważ użycie skilla `name1`, `name2`
  📋 CONTEXT RULES (relevant memory):
    → feedback_X.md: opis...
    ↓
Claude widzi reminder w kontekście przed odpowiedzią
```

### Dlaczego BM25 (v0.2)

BM25 (Best Matching 25) to de-facto standard w search engines — używany przez Google, Elasticsearch, Lucene od ~40 lat. Implementacja w stdlib (~50 linii), bez zewnętrznych zależności. Uwzględnia:

- **IDF** — rzadkie słowa ważniejsze niż częste
- **Length normalization** — krótkie dokumenty nie dostają niesprawiedliwej przewagi
- **Term frequency saturation** — 10. powtórzenie słowa już niewiele dodaje

Plus prosty **stemmer polski** — żeby „wagę"/"waga"/„wagi" matchowały się na wspólny trzon.

**Silent fail** wszędzie — brak configa, broken JSON, prompt 50 KB, sigma Unicode — hook nigdy nie ubija promptu.

---

## Troubleshooting

| Objaw | Diagnoza |
|---|---|
| `tail -f` pokazuje same `NO MATCH` | Keywordy w twoim configu nie pasują do tego jak faktycznie mówisz. Odpal `skill-router-stats.py --days 7` → sekcja „bez matcha" powie które skille są martwe. |
| `CONFIG WARN` w logu | Zły format `skill-rules.json`. Komunikat mówi co poprawić (priority, keywords, typ entry). |
| Hook nie odpala się w ogóle | Sprawdź `~/.claude/settings.json` — czy jest blok `UserPromptSubmit`? Sprawdź `which python3`. |
| Log rośnie w nieskończoność | Hook sam rotuje po 1 MB (`.log.1`). Jeśli nadal duży — `LOG_MAX_BYTES` w `skill-router.py` obniż. |

---

## Licencja

MIT — patrz [LICENSE](LICENSE).

---

*Koncept `UserPromptSubmit` + `skill-rules.json` zainspirowany publicznym projektem [diet103/claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase) (MIT).*
