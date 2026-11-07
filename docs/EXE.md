# GAME.EXE — PvP i kody w multiplayerze

[Projekt](../README.md) · [Pobierz ZIP](https://github.com/arasusx-cyber/evil-islands-mp-tools/releases/latest/download/Evil_Islands_PvP_kody.zip)

## Zawartość

Paczka zawiera 32-bitowy `GAME.EXE` z dwiema zmianami: obrażeniami między graczami (PvP/PK) oraz odblokowaniem poleceń konsoli w multiplayerze. Zachowuje funkcjonalne zmiany historycznych poprawek CHaSE dla silnika 1.06, bez kosmetycznego nadpisania tekstu wersji.

Jest to konkretny zmodyfikowany plik, a nie uniwersalny instalator dla każdej edycji gry. Oznaczenie wersji w samym pliku pozostaje bez zmian.

| Właściwość | Wartość |
| --- | --- |
| Rozmiar GAME.EXE | 3 825 725 bajtów |
| SHA-256 zmodyfikowanego GAME.EXE | `e5fd63f6efe57d13e00603ce994718ca49d38e83c94633ecfd4f7e46b524131c` |

## Instalacja

1. Zamknij grę i zachowaj kopię katalogu `mp`.
2. Zmień nazwę dotychczasowego `GAME.EXE` na `GAME_ORIGINAL.EXE` i zachowaj go.
3. Skopiuj `GAME.EXE` z ZIP-a do katalogu gry.
4. Uruchom grę jak dotychczas. Sesję multiplayer załóż na komputerze z poprawionym plikiem.

## Kody

Na komputerze gospodarza otwórz konsolę klawiszem `~`, wpisz `thingamabob` i zatwierdź Enterem. Przykładowe polecenia:

```text
give 0 money 10000
give 0 exp 10000
```

Polecenia `give` testuj na bazie / ekranie mapy, poza misją. Numer `0` oznacza gracza gospodarza.

## PvP

PvP jest aktywne po uruchomieniu zmodyfikowanej wersji. Zabicie gracza nie dodaje EXP. Gracze nadal mają klasyfikację sojuszników, więc czary ograniczone runą do wrogów mogą ich pomijać.

## Cofnięcie

Zamknij grę, usuń podmieniony `GAME.EXE` i przywróć nazwę `GAME_ORIGINAL.EXE` do `GAME.EXE`.

## Sprawdzenie pliku

Windows PowerShell:

```powershell
Get-FileHash .\GAME.EXE -Algorithm SHA256
```

Wynik powinien odpowiadać sumie w tabeli. Suma identyfikuje zmodyfikowaną paczkę, nie potwierdza zgodności innej instalacji gry. Zakres sprawdzenia opisuje [VALIDATION.md](VALIDATION.md), a źródła poprawek — [NOTICE.md](../NOTICE.md).
