# Edycja parametrów złożonych czarów

W zakładce **Czary** każdy rekord jest przedstawiony osobno, z ID i numerem
prototypu. Lista obejmuje wszystkie rekordy czarów zapisane w MP, w tym
powiązane z plecakiem, podręcznymi czarami, bronią i zbroją oraz rekordy
bez powiązanego przedmiotu. Po wybraniu czaru pokazuje się jego położenie
i niezerowe numery run zapisane w MP.

Nazwy pochodzą z klasycznej tabeli SpellPrototypes: wiersz 0 to Fire Arrow,
wiersz 1 Lightning Arc. Mod może mieć inną kolejność; numery prototypów pozostają
widoczne, a dla nierozpoznanych nazw wyświetla się „Wiersz #...”.

## Obsługa

1. Wczytaj plik i otwórz zakładkę Czary.
2. Dwuklik na parametrze albo Enter otwiera jego edycję.
3. Zastosuj wartość. Oryginał i wynik są widoczne obok siebie.
4. Sprawdź zakładkę Zmiany i zapisz nową kopię MP.

Możesz zmieniać poniższe parametry niezależnie:

| Parametr | Znaczenie | Offset rekordu | Format |
|---|---|---:|---|
| Moc / siła efektu | Obrażenia, leczenie lub inny efekt zależny od czaru | +10 | float32 |
| Zasięg | Zapisany zasięg w jednostkach gry | +22 | float32 |
| Promień obszaru | Promień, a nie pole powierzchni | +14 | float32 |
| Czas trwania | Surowa liczba jednostek czasu gry | +6 | uint32 |
| Bazowy koszt many | Przed przeliczeniem przez inteligencję i zasady gry | +34 | float32 |
| Liczba celów | Zapisana liczba; zachowanie zależy także od typu i flag | +26 | uint32 |
| Wymagany poziom magii | Wymagana umiejętność przy rzucaniu | +62 | uint32 |
| Prędkość / Speed | Pole Speed prototypu; znaczenie zależy od czaru | +18 | float32 |
| Złożoność | Zapisana wartość, odrębna od liczby run | +38 | uint32 |

Nie ma dodatkowego limitu 100 lub 10^9 dla tych pól. Przyjmowane są wartości
nieujemne mieszczące się w swoim formacie. Pola uint32 wymagają liczb
całkowitych. NaN, nieskończoność i przekroczenie zakresu są odrzucane.
Liczby float32 są zaokrąglane do dokładnej reprezentacji przechowywanej w MP.

## Runy specjalne i zachowanie pozostałych danych

Specjalne kody, np. ee1, rr1, dd1, tt1 i aa1, należą do bazy moda. MP przechowuje
numery wierszy run, a nie ich pełne nazwy i kody. Dlatego edytor pokazuje
oryginalne ID run i zachowuje ich osiem bajtów bez przebudowywania.

Zmiana np. mocy nie zmienia automatycznie:

- zestawu run i flag filtrów/wyzwalaczy;
- prototypu i identyfikatora czaru;
- kosztu many, wymaganego poziomu ani złożoności — edytujesz je osobno;
- ceny i nierozpoznanych pól;
- powiązania z pojemnikiem, wyposażeniem lub plecakiem.

W tej wersji nie dodajesz nowego czaru, nie podmieniasz jego rodzaju
i nie wymieniasz run. Zmiana promienia i liczby celów nie przebudowuje
sposobu działania prototypu. Gra lub mod mogą dodatkowo ograniczać albo
przeliczać efekt; po wczytaniu zmienionej kopii sprawdź zachowanie w grze.

## Przykład 10.mp

W testowym 10.mp rekord #22, prototyp 0, jest powiązany z pojemnikiem
#37 w plecaku. Według tabeli referencyjnej to Fire Arrow:

| Pole | Oryginał |
|---|---:|
| Moc | 14 |
| Zasięg | 15 |
| Promień obszaru | 0 |
| Czas trwania | 1 |
| Bazowa mana | 2 |
| Cele | 1 |
| Wymagany poziom magii | 2 |
| Speed | 10 |
| Złożoność | 2 |

Zapisana runa ma ID 10. Referencyjna tabela SpellModifiers wiąże ten numer
z Extra Effect / e1; mod może nadawać temu ID własną nazwę. Drugi zapisany rekord
#15, prototyp 24, w tej konkretnej kopii nie ma powiązanego pojemnika.
Program odczytuje rzeczywistą zawartość wybranego pliku; późniejsze zmiany
wyposażenia są widoczne dopiero po wczytaniu nowego zapisu.

Przykład polecenia (ID 22 dotyczy dołączonego 10.mp):

```text
python editor.py examples/10.mp --set spell.22.effect=140 --set spell.22.range=30 --set spell.22.mana=1 --output 10.spell-copy.mp
```

## Weryfikacja

- Parametry porównano z układem CSpell::Write 0x68B920 i CSpell::Read
  0x68B860 w analizowanym GAME.EXE oraz kodem źródłowym konstruktora czarów.
- Edycje wszystkich obsługiwanych pól przeszły eksport i ponowny odczyt.
- Na 9.mp i 10.mp porównano bajty poza zamierzonymi zmianami, w szczególności
  wszystkie runy, flagi, cenę, ID, prototypy i odwołania.
- Syntetyczny przypadek dwóch gotowych czarów (Lightning Arc podręcznie
  i Fire Arrow w plecaku) z własnymi ID run potwierdził niezależną edycję.
- Zmienione dane z obu oryginalnych przykładów zweryfikowano także
  niezależnym parserem referencyjnym i kodekiem C++.
- Brak testu efektu zmienionych parametrów w uruchomionej grze i własnego
  interaktywnego testu okna w środowisku graficznym.

Źródło referencyjne:
[Kyr4l, tools/um-bot/spells.hpp](https://github.com/Kyr4l/ei-universal-mod/blob/810a9019a57d1b3081e39d50444f3339ba0fa56f/tools/um-bot/spells.hpp).
