# Zakres weryfikacji

[Projekt](../README.md) · [Odtworzenie testów](DEVELOPMENT.md)

## Edytor MP

Projekt zawiera **21 testów unittest**. Obejmują one eksport bez zmian, edycję obsługiwanych pól, zachowanie nierozpoznanych bajtów, zmianę długości nazwy, więcej niż jedną postać, ruch/LOCOMOTION, czary, materiały, ochronę pancerza, naprawę i ładowanie wyposażenia.

Testy sprawdzają również odrzucanie uszkodzonych plików i niepoprawnych wartości oraz ochronę oryginałów i istniejących ścieżek przed nadpisaniem.

Pliki testowe:

| Plik | SHA-256 |
| --- | --- |
| `examples/9.mp` | `3ad7bec3c2824c063fb8d39dc5b9ade87e85d98e5ca89d677871cfc62f6fc9a6` |
| `examples/10.mp` | `c75dae21638f31242523afc64eb77f7f2d214e9e584c87e5887a5b32e6e37068` |

Dołączony kodek C++ umożliwia niezależne sprawdzenie rozpakowanych danych i ponownej serializacji. Sprawdzono także CLI oraz składnię plików Python. Mechanizmy edycji i pliki wejściowe zachowano z ostatniej wersji edytora; tekst pomocy wskazuje dokumenty w `docs/`.

Test integralności nie potwierdza wizualnego lub mechanicznego efektu każdej skrajnej wartości w grze. Aktualne sprawdzenia publikacji nie obejmują uruchamiania całej gry ani interaktywnego testu okna Tkinter.

## GAME.EXE

Paczka zachowuje dokładne bajty wcześniej przygotowanego pliku PvP + kody. Sprawdzono jego nagłówek PE, rozmiar i SHA-256 oraz integralność archiwum. Działanie tej kopii zostało wcześniej potwierdzone w używanej instalacji gry.

Pierwotna modyfikacja obejmowała 11 bajtów i była sprawdzana względem sygnatur historycznych poprawek oraz bloków instrukcji x86. Przy publikacji nie wykonano nowego testu sesji multiplayer i nie rozszerzono zgodności na inne EXE.

Sumy obu archiwów i zmodyfikowanego EXE są dostępne w [dist/SHA256SUMS.txt](../dist/SHA256SUMS.txt) oraz w plikach wydania.
