# Obsługa edytora MP

[Projekt](../README.md) · [Format MP](FORMAT_MP.md) · [Ruch](RUCH_MP.md) · [Czary](CZARY_MP.md) · [Wyposażenie](EKWIPUNEK_MP.md)

## Uruchomienie

Na Windows zainstaluj Python 3.10 lub nowszy z obsługą Tcl/Tk. Wypakuj cały folder i uruchom `URUCHOM.bat` lub `Edytor_MP.pyw`. Nie są potrzebne pakiety pip.

Na Linuxie uruchom `python3 editor.py`; Tkinter może wymagać osobnego pakietu dystrybucji. Tryb skryptowy nie potrzebuje Tkinter, sieci ani serwera.

## Edycja i zapis

1. Wybierz **„Otwórz .mp…”**. Folder `examples/` zawiera pliki testowe.
2. Wybierz zakładkę i parametr. Dwuklik albo Enter otwiera jego edycję.
3. **„Zastosuj”** wprowadza zmianę w pamięci. Kolumny pokazują oryginał i wynik.
4. Zakładka **„Zmiany”** przedstawia komplet zmian. Możesz cofnąć jedno pole lub wszystkie.
5. **„Zapisz zmienioną kopię…”** tworzy nowy plik. **„Kopia oryginału…”** zachowuje wejście bajt w bajt.

Edytor blokuje nadpisanie oryginału i istniejącego pliku, także poprzez dowiązania. Przed zapisaniem sprawdza eksport przez ponowny odczyt, a potem kontroluje bajty zapisane na dysku.

## Przeniesienie kopii do gry

Zamknij grę. Zachowaj oryginalną postać w osobnym miejscu. Umieść wybraną kopię w katalogu `mp` gry pod odpowiednim numerem, np. `10.mp`. Edytor sam nie podmienia pliku używanego przez grę.

## Zakres

Obsługiwany jest kontener postaci `0x114`, wersja `0x74` (116), również z więcej niż jedną postacią. Nie jest to edytor map.

Możesz edytować nazwę/klan, wysokość, EXP i złoto, cechy, ruch, umiejętności, zdolności, parametry zapisanego wyposażenia oraz istniejących czarów. Naprawa i ładowanie wyposażenia uzupełniają bieżącą trwałość lub energię do zapisanych maksimów.

Wysokość jest skalą modelu, nie liczbą centymetrów. Poziomy cech bieżących mogą zostać przeliczone przez grę. HP i mana nie mają tu pojedynczego, bezpośrednio edytowanego pola. Program nie tworzy nowych przedmiotów ani czarów i nie przebudowuje zestawów run.

Nazwy pochodzą z klasycznej bazy. Mod może zmienić kolejność wierszy; sprawdzaj ID i numery prototypów w zakładce struktury. Efekty zmian sprawdzaj na kopii w używanej wersji gry/moda.

## Tryb skryptowy

Lista pól i aktualnych wartości:

```text
python editor.py examples/10.mp --inspect
```

Nowa kopia ze zmianą złota i wysokości:

```text
python editor.py examples/10.mp --set gold=10000 --set m0.height=300 --output 10.edited.mp
```

Naprawa i ładowanie broni/zbroi:

```text
python editor.py examples/10.mp --repair --recharge --output 10.repaired.mp
```

Edycja czaru #22 w dołączonym `10.mp`:

```text
python editor.py examples/10.mp --set spell.22.effect=140 --set spell.22.mana=1 --output 10.spell.mp
```

ID czaru jest właściwe dla konkretnego pliku. `--set` można powtarzać, a `--output` musi wskazywać nową nazwę. Kodowanie nazw wybierzesz przez `--encoding cp1250`, `cp1251` lub `cp1252`.
