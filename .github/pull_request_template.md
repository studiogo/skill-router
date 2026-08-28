**Co ta zmiana robi**

Jedno zdanie.

**Dlaczego**

Odnośnik do zgłoszenia albo opis sytuacji przy pracy, która do tego doprowadziła.

**Jak to sprawdziłeś**

Wynik uruchomienia hooka wprost z terminala, przed zmianą i po:

```bash
echo '{"prompt":"TU PROMPT"}' | python3 skill-router.py; echo "kod wyjścia: $?"
```

```
```

Jeśli zmiana dotyczy dopasowania albo rankingu, dołóż statystyki z własnej konfiguracji z kilku dni: `python3 skill-router-stats.py --days 7`.

**Warunki, których projekt nie łamie**

- [ ] Zero zależności zewnętrznych — sama biblioteka standardowa Pythona.
- [ ] Hook kończy się kodem 0 na każdej ścieżce, także przy złym JSON-ie, braku konfiguracji i braku katalogu z pamięcią.
- [ ] Nie blokuje ani nie przepisuje promptu.
- [ ] Istniejące `skill-rules.json` działa dalej bez przeróbek. Jeśli nie — opisałem to niżej.
- [ ] Nic nie wychodzi na zewnątrz: żadnej telemetrii, zdalnego logu ani sprawdzania wersji w sieci.
- [ ] Nie wkleiłem swojej prywatnej konfiguracji, nazw klientów ani ścieżek ze swojego katalogu domowego.

**Zgodność wstecz**

Napisz „bez zmian" albo opisz, co użytkownik musi poprawić po aktualizacji.

**Długość wyniku**

To, co hook dopisuje do kontekstu, zjada okno kontekstu przy każdym prompcie. Napisz „bez zmian" albo o ile się wydłużyło i po co.

**Dokumentacja**

- [ ] Zmiana zachowania jest opisana w README, w sekcji, której dotyczy.
- [ ] Nie dotyczy.
