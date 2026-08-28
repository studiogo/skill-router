---
name: Błąd instalacji albo działania
about: Instalator nie przeszedł, hook się nie odpala, skrypt się wywraca
title: '[BŁĄD] '
labels: błąd
assignees: ''
---

**Co się dzieje**

Jedno zdanie.

**Jak to powtórzyć**

1.
2.
3.

**Czego się spodziewałeś**

**Komunikat błędu**

Pełny ślad wykonania, jeśli jest.

```
```

**Czy hook w ogóle się odpala**

Wynik uruchomienia wprost z terminala, z pominięciem Claude Code:

```bash
echo '{"prompt":"test"}' | python3 ~/.claude/hooks/skill-router.py; echo "kod wyjścia: $?"
```

```
```

Hook ma zawsze kończyć się kodem 0, nawet gdy nic nie podpowiada. Inny kod to sam w sobie błąd.

**Podpięcie hooka**

Blok `UserPromptSubmit` z `~/.claude/settings.json`. Usuń z niego wszystko, co nie dotyczy skill-router.

```json
```

**Log**

`tail -30 ~/.claude/hooks/skill-router.log`

```
```

**Wersja i system**

- Wersja skill-router:
- Wynik `python3 --version` i `which python3`:
- System:
- Sposób instalacji: install.sh / ręcznie
