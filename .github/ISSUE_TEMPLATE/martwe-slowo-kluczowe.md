---
name: Hook nie podpowiada tego, co powinien
about: Wpisałeś prompt, a router nie zasugerował właściwego skilla albo podpowiedział nie ten
title: '[DOPASOWANIE] '
labels: dopasowanie
assignees: ''
---

**Prompt, który wpisałeś**

Słowo w słowo, razem z odmianą i znakami diakrytycznymi. To najważniejsza informacja w całym zgłoszeniu.

```
```

**Jakiego skilla się spodziewałeś**

Nazwa skilla, który powinien się podpowiedzieć.

**Co hook wypisał**

Wklej to, co zobaczyłeś, albo napisz „nic". Log: `tail -20 ~/.claude/hooks/skill-router.log`.

```
```

**Fragment konfiguracji**

Tylko ten jeden wpis ze `skill-rules.json`, którego dotyczy sprawa. Nie wklejaj całego pliku — u większości ludzi są w nim nazwy klientów i projektów.

```json
```

**Sprawdzenie poza Claude Code**

Wynik uruchomienia wprost z terminala:

```bash
echo '{"prompt":"TU TWÓJ PROMPT"}' | python3 ~/.claude/hooks/skill-router.py
```

```
```

**Statystyki, jeśli to dzieje się od dłuższego czasu**

`python3 ~/.claude/hooks/skill-router-stats.py --days 7` — wystarczy sekcja o słowach bez trafienia.

**Wersja i system**

- Wersja skill-router:
- Wynik `python3 --version`:
- System:
