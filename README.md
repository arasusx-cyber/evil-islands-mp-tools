# Evil Islands MP Tools

Edytor postaci multiplayer `.mp` do **Evil Islands: Klątwa Zagubionej Duszy** oraz `GAME.EXE` z PvP i kodami w multiplayerze.

**[⬇ Pobierz GAME.EXE z rozszerzonym kreatorem MP](https://github.com/arasusx-cyber/evil-islands-mp-tools/releases/download/v1.0.0/Evil_Islands_1.06_PvP_Kody_Kreator.zip)** · [Instrukcja i suma kontrolna](docs/EXE.md#wariant-z-rozszerzonym-kreatorem-mp)

Osobny wariant GAME.EXE z PvP i konsolą kodów. W kreatorze postaci multiplayer podnosi limit wzrostu do **1000** i daje **75 dodatkowych punktów** na siłę, zręczność i inteligencję.

**[⬇ Pobierz edytor MP](https://github.com/arasusx-cyber/evil-islands-mp-tools/releases/latest/download/Evil_Islands_MP_Editor_Python.zip)** · **[⬇ Pobierz GAME.EXE — PvP i kody](https://github.com/arasusx-cyber/evil-islands-mp-tools/releases/latest/download/Evil_Islands_PvP_kody.zip)** · [English](README.en.md)

## Edytor MP

| Obszar | Możliwości |
| --- | --- |
| Postać | Nazwa i klan, wysokość, złoto, EXP, cechy, umiejętności i zdolności |
| Ruch | Prędkości, współczynniki ruchu i LOCOMOTION: chodzenie / lewitacja |
| Ekwipunek | Trwałość, energia i jej regeneracja, materiał, waga, obrażenia i ochrona |
| Czary | Moc, zasięg, promień, czas, mana i inne parametry istniejących czarów |
| Eksport | Porównanie zmian, cofanie i zapis do nowej kopii |

### Uruchomienie

1. Zainstaluj **Python 3.10+ z Tcl/Tk**. Dodatkowe pakiety pip nie są potrzebne.
2. Wypakuj cały ZIP i uruchom **URUCHOM.bat** albo **Edytor_MP.pyw**.
3. Otwórz postać `.mp`, zmień parametry i wybierz **„Zapisz zmienioną kopię…”**.

Edytor obsługuje pliki postaci z nagłówkiem `0x114`, wersją `0x74`. Zapisuje nowy plik, chroniąc oryginał przed nadpisaniem. Przeniesienie wybranej kopii do folderu `mp` gry opisuje [instrukcja edytora](docs/EDITOR.md).

## GAME.EXE — PvP i kody

Osobna paczka włącza obrażenia między graczami i polecenia konsoli w multiplayerze. Jest przygotowana dla konkretnego pliku EXE; instalacja, zgodność, komendy i cofnięcie zmian są w [instrukcji GAME.EXE](docs/EXE.md).

Na komputerze gospodarza otwórz konsolę klawiszem `~`:

```text
thingamabob
give 0 money 10000
give 0 exp 10000
```

Polecenia `give` wykonuj na bazie / ekranie mapy, poza misją. Przed podmianą EXE zachowaj jego oryginał i kopię postaci.

## Dokumentacja i rozwój

[Obsługa edytora](docs/EDITOR.md) · [Czary](docs/CZARY_MP.md) · [Wyposażenie](docs/EKWIPUNEK_MP.md) · [Ruch](docs/RUCH_MP.md) · [Format MP](docs/FORMAT_MP.md) · [Testy](docs/VALIDATION.md) · [Dla programistów](docs/DEVELOPMENT.md)

Kod edytora: [GPL-3.0-or-later](LICENSE.txt). Autorzy, źródła i zakres licencji: [NOTICE.md](NOTICE.md).
