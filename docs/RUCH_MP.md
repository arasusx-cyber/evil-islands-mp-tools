# Ruch w zapisie postaci MP

Offsety są liczone od początku bloku parametrów danej postaci, a nie od
początku skompresowanego pliku. Wszystkie sześć wartości liczbowych to
little-endian float32, a LOCOMOTION jest uint32.

| Parametr | Offset | Wartość w 9.mp i 10.mp | Klucz w edytorze |
|---|---|---|---|
| Współczynnik ruchu podstawowy | +0x24 | 1 | m0.move.base |
| Współczynnik ruchu bieżący | +0x28 | 1 | m0.move.current |
| Bieg | +0x34 | 0,46666669845581055 | m0.move.run |
| Chód | +0x38 | 0,20000001788139343 | m0.move.walk |
| Skradanie / przyklęk | +0x3C | 0,1600000113248825 | m0.move.sneak |
| Pełzanie leżąc | +0x40 | 0,12506668269634247 | m0.move.crawl |
| LOCOMOTION: kod trybu ruchu | +0x60 | 1 | m0.move.locomotion |

Akcje (podstawa / bieżące) są osobnymi float32 pod +0x2C/+0x30; oba mają
15 w plikach testowych. Są też pokazane w zakładce Ruch. Nie należy
utożsamiać ich bezpośrednio z prędkością przemieszczania.

Są to wartości zapisane w MP. Edytor nie przelicza ich na m/s ani km/h.
Mnożniki i prędkości edytuje się oddzielnie. Gra i dodatki mogą dodatkowo
przeliczać wartości bieżące.

## Pozycje w konkretnych plikach

| Pole | Offset danych 9.mp | Offset danych 10.mp |
|---|---|---|
| Początek parametrów | 0x641 | 0x51D |
| Mnożnik podstawowy | 0x665 | 0x541 |
| Mnożnik bieżący | 0x669 | 0x545 |
| Bieg | 0x675 | 0x551 |
| Chód | 0x679 | 0x555 |
| Skradanie | 0x67D | 0x559 |
| Pełzanie | 0x681 | 0x55D |
| LOCOMOTION | 0x6A1 | 0x57D |

## Jak ustalono pola

1. Oryginalna dokumentacja SpellAddon, tabela `mptrans`, wymienia indeksy
   9/10 jako `movecoeff.natural/total`, 11/12 jako `actionscoeff.natural/total`,
   13–16 jako `runspeed/walkspeed/crawlspeed/liespeed`. Indeks odpowiada
   offsetowi pomnożonemu przez 4. Te same indeksy dla siły, EXP i udźwigu
   zgadzają się z rozpoznanymi polami cech i EXP.
2. Nagłówki bazy RaceModels podają cztery pozycje `Speed Run/Walk/Sneak/Crawl`
   w tej kolejności. Dlatego nazwy `crawlspeed/liespeed` przetłumaczono
   w interfejsie jako skradanie/przyklęk i pełzanie leżąc.
3. Analiza statyczna analizowanego GAME.EXE:
   - funkcja 0x5136D0 tworzy parametry na podstawie bazy;
   - 0x513826 ustawia cel na blok parametrów +0x34;
   - 0x513829–0x513849 kopiuje cztery kolejne wartości prędkości z RaceModels;
   - 0x5138AD czyta DWORD z RaceModels +0x14, a 0x5138B0 zapisuje go
     do bloku parametrów +0x60; to pole `Secondary Locomotion`;
   - 0x528800 zapisuje 0x704 bajty tego bloku.
4. Zmodyfikowane pliki ponownie odczytano i porównano bajtowo. Eksport kopii
   z podwojonymi prędkościami sprawdzono również niezależnym kodekiem C++.

## LOCOMOTION i regeneracja

MP zapisuje kod LOCOMOTION skopiowany z bazy RaceModels pod offsetem +0x60.
Interfejs udostępnia **1 = chodzenie, 2 = lewitacja**. Mapowanie potwierdzono
w próbach z grą i BalanceTool. Inne wartości pozostają surowymi kodami uint32
i nie są automatycznie zmieniane na 1 lub 2. W obu oryginalnych przykładach
wartość wynosi 1.

Bezpośrednie tempo regeneracji HP i wigoru nie ma potwierdzonego pola MP.
Poziomy zdolności Regeneracja i Odnowa są osobnymi polami 0–3.

## Kopia testowa

`examples/10.ruch-x2.mp` ma podwojone tylko cztery prędkości z oryginalnego
10.mp. Mnożniki, akcje, LOCOMOTION, nazwa, wzrost, EXP, złoto i reszta danych
pozostały niezmienione. Nie uruchomiono jej w grze; jest do własnej próby.
Bezpieczny eksport nadal tworzy nowe pliki i blokuje nadpisywanie oryginałów.

## Źródła

- [SpellAddonInfo.txt — tabela mptrans](https://github.com/Kyr4l/ei-universal-mod/blob/810a9019a57d1b3081e39d50444f3339ba0fa56f/tools/SpellAddon_20.5/!SpellAddonX/SpellAddonInfo.txt).
- [Nagłówki RaceModels](https://github.com/Kyr4l/ei-universal-mod/blob/810a9019a57d1b3081e39d50444f3339ba0fa56f/tools/um-multitool/db_headers_generated.hpp).
- Pliki testowe 9.mp, 10.mp oraz analizowany GAME.EXE. Paczka EXE jest dostępna osobno.

Rozpoznanie struktury i test integralności pliku nie zastępują próby wczytania
zmiany przez daną wersję gry i moda.
