# Jak pomóc przy skill-router

Dzięki, że chcesz się dołożyć. Ten projekt jest mały z założenia: jeden hook w Pythonie, zero zależności, ma działać na czystym Pythonie 3.7+ na macOS i Linuksie. Poniżej masz, co jest tu cenne i czego nie przyjmę.

## Co jest tu najcenniejsze

**Zgłoszenie martwego dopasowania.** Najbardziej pomaga informacja, że hook nie zasugerował skilla, choć powinien, albo zasugerował nie ten. To jest sedno tego narzędzia i tego nie da się zbadać bez cudzych promptów.

Dobre zgłoszenie ma:

- prompt, który wpisałeś, słowo w słowo,
- odpowiedni fragment `skill-rules.json` (nazwy skilli i słowa kluczowe — bez treści prywatnych),
- co hook wypisał, a co miał wypisać,
- wynik `python3 skill-router-stats.py --days 7`, jeśli chodzi o skuteczność w dłuższym okresie.

**Uwaga na własne dane.** Nie wklejaj całego `skill-rules.json` ani plików reguł z pamięci. U większości ludzi siedzą tam nazwy klientów, projektów i wewnętrzne skróty. Przytnij do kilku wpisów, których zgłoszenie dotyczy, a nazwy zastąp czymś neutralnym. To samo dotyczy loga i wyniku statystyk — nazwy skilli bywają wymowne.

**Odmiana polska, która się nie łapie.** Dopasowanie jest po rdzeniu słowa i po zdjęciu znaków diakrytycznych. Jeśli znajdziesz formę, która wymyka się temu podejściu, napisz ją wprost razem z rdzeniem z konfiguracji.

**Ranking reguł, który wypycha rzecz ważną poza pierwszą trójkę.** Podaj prompt, nazwy plików reguł i to, która reguła wypadła. Punktacja BM25 z progami siedzi na górze `skill-router.py`.

## Zanim otworzysz zgłoszenie

1. Sprawdź log: `tail -20 ~/.claude/hooks/skill-router.log`.
2. Odpal statystyki: `python3 ~/.claude/hooks/skill-router-stats.py --days 7`. Sekcja o słowach bez trafienia zwykle sama pokazuje przyczynę.
3. Sprawdź, czy hook w ogóle się odpala — blok `UserPromptSubmit` w `~/.claude/settings.json`.

## Zmiany w kodzie

Uruchom hook bez Claude Code, wprost z terminala:

```bash
echo '{"prompt":"Zrób karuzelę na LinkedIn"}' | python3 skill-router.py
```

Zasady, które obowiązują każdą zmianę:

- **Zero zależności.** Tylko biblioteka standardowa Pythona. Zgłoszenie wymagające `pip install` odrzucam bez dyskusji.
- **Hook nigdy nie ubija promptu.** Każda ścieżka błędu kończy się kodem wyjścia 0. Zły JSON, brak konfiguracji, dziwny Unicode, prompt na 50 KB — hook milczy i przepuszcza.
- **Tryb podpowiedzi, nie blokady.** Hook sugeruje, nigdy nie wstrzymuje ani nie przepisuje promptu.
- **Zgodność wstecz z konfiguracją.** Istniejące `skill-rules.json` ma działać po aktualizacji bez przeróbek.
- **Krótki wynik.** To, co hook dopisuje do kontekstu, zjada okno kontekstu użytkownika przy każdym prompcie. Zmiana, która wydłuża wynik, musi to uzasadnić.

Sprawdź swoją zmianę na własnej konfiguracji przez kilka dni, zanim ją zgłosisz. Statystyki przed i po są mocnym argumentem.

## Czego nie przyjmę

- Zależności zewnętrznych, także „lekkich".
- Zamiany BM25 na model uczony albo na wywołanie modelu językowego. Hook chodzi przy każdym prompcie i ma być natychmiastowy oraz darmowy.
- Wysyłania czegokolwiek na zewnątrz — telemetrii, zdalnego logu, sprawdzania wersji w sieci.
- Trybu blokującego prompt.
- Wsparcia dla Windowsa, jeśli komplikuje kod ścieżek. Zgłoszenie samego problemu jest mile widziane.
- Mojej prywatnej konfiguracji jako domyślnej. `skill-rules.example.json` ma być czytelnym przykładem, nie czyimś systemem pracy.

## Formalności

- Język zgłoszeń: polski albo angielski, oba są w porządku.
- Zatwierdzenia zmian: jedno zdanie w trybie rozkazującym, co zmienia. Bez wymaganego wzorca.
- Zmieniasz zachowanie dopasowania — dopisz to do README, do sekcji, której dotyczy.
- Licencja: MIT. Wysyłając zmianę, godzisz się na wydanie jej na tej licencji.

Rozmowa o pomyśle przed napisaniem kodu oszczędza czas obu stronom. Otwórz zgłoszenie i opisz, co chcesz zrobić.
