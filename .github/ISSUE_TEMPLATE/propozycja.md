---
name: Propozycja zmiany
about: Pomysł na nowe zachowanie hooka albo na zmianę sposobu dopasowania
title: '[POMYSŁ] '
labels: pomysł
assignees: ''
---

**Jaki problem to rozwiązuje**

Opisz sytuację przy pracy, nie rozwiązanie. Co Ci przeszkadza dzisiaj i jak często.

**Co proponujesz**

**Jak sobie radzisz teraz**

Co próbowałeś w konfiguracji, zanim uznałeś, że trzeba zmienić kod.

**Trzy warunki, których projekt nie łamie**

Zaznacz, że propozycja je spełnia. Zgłoszenie łamiące którykolwiek z nich zamknę.

- [ ] Nie wymaga żadnej zależności zewnętrznej — sama biblioteka standardowa Pythona.
- [ ] Nie wysyła nic na zewnątrz i nie wywołuje modelu językowego. Hook chodzi przy każdym prompcie i ma być natychmiastowy oraz darmowy.
- [ ] Nie blokuje ani nie przepisuje promptu. Router podpowiada.

**Wpływ na istniejące konfiguracje**

Czy czyjeś `skill-rules.json` przestanie działać po tej zmianie? Jeśli tak, opisz, co trzeba w nim poprawić.

**Wpływ na długość wyniku**

To, co hook dopisuje do kontekstu, zjada okno kontekstu przy każdym prompcie. Jeśli propozycja wydłuża wynik, napisz o ile i po co.
