# skill-router

**Automatyczne przypomnienia o Twoich skillach w Claude Code.** Claude zapomina o kartkach procedur po długiej sesji. `skill-router` to drugi asystent — czyta każdy Twój prompt, matchuje go ze słownikiem skilli i szepcze Claude'owi: *„sprawdź kartkę 13"*.

Jeden hook w Pythonie. **Zero zależności** — `pip install` nie jest potrzebny, tylko Python 3.7+ (macOS/Linux ma wbudowany).

---

## Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/studiogo/skill-router/main/install.sh | bash
```

Kopiuje 3 pliki do `~/.claude/hooks/`, podpina hook w `~/.claude/settings.json` (z backupem), stawia startowy `skill-rules.example.json`. Nie nadpisze istniejącej konfiguracji.

**To wszystko.** W nowej sesji Claude Code wpisz coś ze słowem kluczowym z config'a i zobaczysz:

```
$ echo '{"prompt":"Zrób karuzelę na LinkedIn"}' | python3 skill-router.py
🎯 SKILL ACTIVATION: Rozważ użycie skilla `create-carousel`
```

## Co robi

1. **Słucha każdego promptu** (hook `UserPromptSubmit`) i normalizuje polskie diakrytyki — `„zrób karuzelę"` matchuje keyword `„zrob karuzele"`.
2. **Sugeruje do 3 skilli** gdy trafi na słowo kluczowe z Twojego configu. Tryb SUGGEST — nigdy nie blokuje promptu.
3. **Loguje każde uruchomienie** do `~/.claude/hooks/skill-router.log` (auto-rotacja po 1 MB).

## Konfiguracja

### Pierwszy config przez wizarda

```bash
python3 ~/.claude/hooks/skill-router-config-init.py
```

Pyta o kategorie (content, inbox, scheduling, image-gen, dev, personal) i generuje startowy `~/.claude/skill-rules.json`.

### Ręczna edycja

```json
{
  "version": "1.0",
  "skills": {
    "create-carousel": {
      "keywords": ["carousel", "karuzel", "slajd"],
      "priority": "high"
    }
  }
}
```

> **Tip: używaj rdzeni słów.** Matching jest substring po diakrytykach, więc `"karuzel"` łapie *karuzela / karuzelę / karuzeli / karuzele*. Jedna forma bazowa = pełna odmiana po polsku.

## Komendy

```bash
# podgląd loga na żywo
tail -f ~/.claude/hooks/skill-router.log

# statystyki: match rate, top 10 skilli, dead keywords
python3 ~/.claude/hooks/skill-router-stats.py
python3 ~/.claude/hooks/skill-router-stats.py --days 7
```

## Troubleshooting

| Objaw | Diagnoza |
|---|---|
| Same `NO MATCH` w logu | Keywordy w configu nie pasują do tego jak mówisz. Odpal stats → sekcja „bez matcha" powie które skille są martwe. |
| `CONFIG WARN` | Zły format `skill-rules.json`. Komunikat mówi co poprawić. |
| Hook nie odpala się | Sprawdź `~/.claude/settings.json` → blok `UserPromptSubmit`. `which python3` musi zwracać ścieżkę. |

---

<details>
<summary><strong>⚡ Advanced — dla power userów systemu pamięci</strong></summary>

Jeśli trzymasz własne zasady pracy w `~/.claude/projects/*/memory/feedback_*.md` i `memory/rules/*.md` (pliki markdown z YAML frontmatter'em), hook może je automatycznie **wstrzykiwać do kontekstu** gdy są relevantne do promptu.

Przykład z aktywnym systemem pamięci:

```
$ echo '{"prompt":"Zrób karuzelę na LinkedIn o AI agentach"}' | python3 skill-router.py
🎯 SKILL ACTIVATION: Rozważ użycie skilla `create-carousel`

📋 CONTEXT RULES (relevant memory):
  → feedback_carousel_default_style_b.md: Style B jest domyślny...
  → feedback_linkedin_api.md: Nie publikować przez Postiz — używać LinkedIn API...
```

Jeśli **nie masz** plików `feedback_*.md` w swoim systemie, hook milczy o tym — widzisz tylko SKILL ACTIVATION (identycznie jak w quick start powyżej).

### Jak to działa pod spodem

```
prompt → normalize (diakrytyki + stemmer polski)
       ↓
       ├─ A) SKILL ACTIVATION          ← substring match z skill-rules.json
       └─ B) CONTEXT RULES (opt-in)    ← BM25 ranking na memory/
                                          - IDF × TF × length normalization
                                          - boost dla filename/description (3×)
                                          - priority boost (critical=10×, high=3×, medium=1×, low=0.3×)
                                          - min 2 unique hits, min score 3.0
```

**Dlaczego BM25:** to de-facto standard w search engines (Google, Elasticsearch, Lucene, ~40 lat). Stdlib-only implementacja (~70 linii) = zero deps.

### Priority boost

Dodaj w YAML frontmatter reguły:

```yaml
---
name: Firewall legal
description: Klauzula §9.4 — wabienie klientów
priority: critical   # ← critical/high/medium/low
---
```

Critical × 10 multiplier zapewnia że bezpieczeństwo i legal praktycznie nigdy nie wypadną z top 3.

### Auto-mapowanie skilli z SKILL.md

Zamiast ręcznie pisać `skill-rules.json`, wygeneruj z frontmatter'ów:

```bash
python3 ~/Projects/skill-router/scripts/gen-skill-rules.py
```

Skrypt:
- skanuje `~/.claude/skills/*/SKILL.md`
- parsuje `description:` → wyciąga quoted trigger phrases (`"napisz post"`, `"zrób X"`)
- dodaje nazwę skilla jako fallback keyword
- zachowuje istniejące manualne priority
- robi timestamped backup `skill-rules.json.bak-YYYYMMDD-HHMMSS`

### Silent fail wszędzie

Brak configa, broken JSON, prompt 50 KB, unusual Unicode, brak `memory/` — hook nigdy nie ubija promptu. Exit 0 zawsze.

### Tuning pod swój korpus

Progi rankingu (`PRIORITY_BOOST`, `CONTEXT_MIN_SCORE`, `CONTEXT_MIN_SCORE_NO_SKILL`, `CONTEXT_MIN_QUERY_TOKENS`) są stałymi na początku `skill-router.py`. Defaulty są konserwatywne — jeśli masz za dużo szumu w meta-rozmowach, zaostrzaj lokalnie. Edytuj wartości w swojej kopii `~/.claude/hooks/skill-router.py` — nie ma osobnego pliku config, bo chcemy minimum ruchomych części.

</details>

---

## Wersje

- **v0.1.0** — [release](https://github.com/studiogo/skill-router/releases/tag/v0.1.0) — podstawa (tylko skill activation). Idealna jeśli nie masz systemu pamięci.
- **v0.2.0** — [release](https://github.com/studiogo/skill-router/releases/tag/v0.2.0) — dodany BM25 context rules z `memory/feedback_*.md`.
- **v0.3.0** (aktualna) — [release](https://github.com/studiogo/skill-router/releases/tag/v0.3.0) — priority boost + rules/*.md w corpus + auto-mapa skilli.

Do filmu wprowadzającego skill-router polecamy **v0.1.0** (prostsza) — instaluje się tą samą komendą, tylko podmień `main` na `v0.1.0`:

```bash
curl -fsSL https://raw.githubusercontent.com/studiogo/skill-router/v0.1.0/install.sh | bash
```

## Licencja

MIT — patrz [LICENSE](LICENSE).

---

*Koncept `UserPromptSubmit` + `skill-rules.json` zainspirowany publicznym projektem [diet103/claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase) (MIT).*
