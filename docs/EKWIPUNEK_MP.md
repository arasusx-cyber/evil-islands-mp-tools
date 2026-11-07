# Rozszerzona edycja wyposażenia

W zakładce **Ekwipunek** zmienisz energię, jej regenerację, pojemność magiczną,
materiał i ochronę pancerza. Każda zmiana ma porównanie z oryginałem i funkcję
cofnięcia. Eksport nadal tworzy nową kopię MP.

## Rozpoznane pola

Offsety poniżej są względne względem początku bloku danych przedmiotu,
po rozpakowaniu MP. Nie są to adresy w pamięci gry.

| Parametr | Offset | Typ | Klucz, przykładowe ID |
|---|---:|---|---|
| Materiał | +4 oraz nagłówek obiektu +8 | uint16 | `item.30.material` |
| Trwałość / maksimum | +8 / +12 | float32 | `item.30.durability`, `max_durability` |
| Energia / maksimum | +16 / +20 | float32 | `item.30.energy`, `max_energy` |
| Regeneracja energii | +24 | float32 | `item.30.energy_regen` |
| Waga | +28 | float32 | `item.30.weight` |
| Pojemność magiczna, Slots | +48 | uint32 | `item.30.spell_capacity` |
| Ochrona: zestaw 1 | +52…+76 | 7 × float32 | `item.2.protection.1.fire` |
| Ochrona: zestaw 2 | +80…+104 | 7 × float32 | `item.2.protection.2.fire` |

Energia, regeneracja, Slots i trwałość dotyczą broni oraz zbroi. Dwa zestawy
ochrony występują tylko w zbroi. Edycja materiału obejmuje także łupy.
Numery 30 i 2 pochodzą z dołączonego 10.mp; inny plik może mieć inne ID.

## Regeneracja energii przedmiotów

Analizowany GAME.EXE ma pod 0x6A0070 procedurę, która odnawia energię:
dodaje współczynnik pomnożony przez maksymalną energię i ogranicza wynik
do maksimum. Współczynnik pamięciowy +0x30 jest serializowany do MP pod
+24 przez wspólny writer przedmiotów 0x6A0360.

| Wartość | Znaczenie przy jednej aktualizacji przedmiotu |
|---:|---|
| 0,001 | 0,1% maksymalnej energii |
| 0,01 | 1% maksymalnej energii |
| 0,1 | 10% maksymalnej energii |
| 1 | Cały zapas, z ograniczeniem do maksimum |
| 0 | W tej wersji GAME.EXE: natychmiastowe uzupełnienie do maksimum |

Zero nie jest wyłączeniem regeneracji. Nie ustalono przeliczenia częstotliwości
tej procedury na sekundy. Mod może zmieniać procedurę lub jej częstotliwość.
Pole nie dotyczy zdrowia ani wigoru bohatera.

## Ochrona pancerza

Każdy zestaw zawiera kolejno: kłute (`piercing`), cięte (`slashing`),
obuchowe (`bludgeoning`), ogień (`fire`), kwas (`acid`), błyskawice
(`lightning`) i ogólne (`general`). Są to wartości pochłaniania, nie procenty.

Obie tablice są zapisane oddzielnie. Edytor nie zgaduje, że jedna zmiana
powinna zostać skopiowana do drugiej. Możesz zmienić jeden rodzaj ochrony
lub obie tablice, używając osobnych pól.

Mapowanie: reader 0x6A3A70 / writer 0x6A3AA0 zapisuje dwie tablice po
0x1C bajtów po wspólnym bloku przedmiotu. Kolejność rodzajów obrażeń jest
zgodna z nagłówkami Armors/RaceModels z DBEditor.

## Materiał

Lista nazw jest klasyczna, np. 19 Silicon, 24 Mithrill. W modzie należy
sprawdzić numery materiałów. Można wpisać surowy uint16, ale gra musi
mieć wskazany wiersz w swojej bazie; nieistniejące ID może uniemożliwić
wczytanie przedmiotu.

ID materiału występuje dwukrotnie. Edytor aktualizuje oba miejsca razem,
a cofnięcie pola przywraca oba. Zmieniony prototyp materiału może wpływać
na wygląd i sposób obsługi przedmiotu, ale zapisane parametry liczbowe
nie są automatycznie przebudowywane z bazy. Obrażenia, ochronę, energię
i trwałość ustawiasz niezależnie.

## Naprawa i ładowanie

Przyciski ustawiają bieżącą trwałość albo energię na aktualne maksimum
danego przedmiotu. Uwzględniają maksimum zmienione w edytorze. Działają
na całej zapisanej broni i zbroi, również w plecaku; nie zmieniają mikstur,
łupów, czarów i pozostałych obiektów. W razie niepoprawnej wartości
operacja jest cofana w całości.

Tryb skryptowy:

```text
python editor.py 10.mp --repair --recharge --output 10.naprawione.mp
python editor.py 10.mp --set item.30.energy_regen=0.01 --output 10.regen.mp
```

## Zmysły postaci

Dodano podstawę wzroku oraz podstawę i wartość bieżącą noktowizji oraz
wykrywania życia. Offsety: +0xB0, +0xB8/+0xBC i +0xC0/+0xC4 w bloku
parametrów postaci. Zasięg wzroku bieżący jest już dostępny jako `m0.sight`.
Gra może przeliczać wartości bieżące z podstaw i efektów.

## Co wymaga dalszego rozpoznania

Bezpośrednie tempo regeneracji HP i wigoru nie ma jeszcze potwierdzonego
pola w MP. Kod gry używa do tego osobnej struktury; nie przepisano jej
adresów na offsety pliku. Zdolności Regeneracja/Odnowa 0–3 są dostępne.

Skład specjalnych run jest zachowywany. Tabela SpellModifiers w modzie może różnić się od klasycznej bazy, dlatego
nie używa się jej do przebudowy gotowych czarów ani do podmiany run.

Szybkości ataku i zasięgu konkretnej broni nie dodano bez potwierdzonego
mapowania ich edytowalnych odpowiedników w rekordzie MP.

## Weryfikacja i źródła

- 21 testów jednostkowych, w tym eksport każdego z 268 pól w 9.mp.
- Oba rzeczywiste pliki: zmiana ochrony, regeneracji, Slots, materiału,
  zmysłów i długości nazwy; niezależny kodek/parser C++ odtworzył dokładnie
  te same bajty. Runy i bloki czarów pozostają zachowane.
- Sprawdzono rzeczywisty CLI z naprawą i ładowaniem uszkodzonego wyposażenia.
- Nie wykonano testu działania nowych parametrów w uruchomionej grze.
- Analizowany GAME.EXE oraz pliki testowe 9.mp i 10.mp.
- [Dokumentacja SpellAddon, mptrans](https://github.com/Kyr4l/ei-universal-mod/blob/810a9019a57d1b3081e39d50444f3339ba0fa56f/tools/SpellAddon_20.5/!SpellAddonX/SpellAddonInfo.txt).
- [Nagłówki DBEditor](https://github.com/Kyr4l/ei-universal-mod/blob/810a9019a57d1b3081e39d50444f3339ba0fa56f/tools/um-multitool/db_headers_generated.hpp).
