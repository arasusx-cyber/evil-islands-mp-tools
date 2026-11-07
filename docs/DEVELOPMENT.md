# Rozwój, testy i pakowanie

[Projekt](../README.md) · [Format MP](FORMAT_MP.md) · [Walidacja](VALIDATION.md)

Python 3.10+ i biblioteka standardowa wystarczają do testów i CLI. Tkinter jest potrzebny tylko do okna. Kodek C++ wymaga kompilatora C++17.

## Testy

W katalogu repozytorium:

```bash
python -m py_compile editor.py mp_core.py Edytor_MP.pyw scripts/build_packages.py
python -m unittest discover -s tests -v
```

Niezależny kodek referencyjny:

```bash
g++ -std=c++17 -O2 reference/check_reference.cpp -o check_mp
./check_mp examples/9.mp 9.raw
./check_mp examples/10.mp 10.raw
```

Przykład eksportu przez CLI:

```bash
python editor.py examples/10.mp --set gold=12345 --output exports/10.edited.mp
```

Folder docelowy musi istnieć, a plik docelowy musi mieć nową nazwę.

GitHub Actions uruchamia kontrolę składni, testy unittest i dekodowanie przykładów przez kodek C++.

## Paczki wydania

Samo archiwum edytora:

```bash
python scripts/build_packages.py
```

Obie paczki — z już zmodyfikowanym plikiem EXE:

```bash
python scripts/build_packages.py --game-exe /sciezka/do/GAME.EXE
```

Skrypt nie patchuje gry. Akceptuje wyłącznie znany rozmiar i SHA-256 zmodyfikowanej kopii, opisane w [EXE.md](EXE.md). Dla innego pliku kończy działanie przed zapisem wyników.

Wyniki powstają w `dist/`: ZIP edytora, opcjonalny ZIP GAME.EXE i `SHA256SUMS.txt`. ZIP-y mają stałe metadane i uporządkowaną zawartość. Parametr `--output-dir` zmienia katalog wyjściowy.

Zachowuj nagłówki GPL i informacje o źródłach. Identyfikatory run/prototypów i nierozpoznane dane MP pozostawiaj bez przebudowy, dopóki nie ma zweryfikowanego mapowania.
