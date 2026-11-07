# Format postaci MP — zakres użyty w edytorze

Wszystkie liczby wielobajtowe są little-endian. Obsługiwana jest postać
multiplayer `0x114`, wersja `0x74` (116).

## Kontener

| Offset w pliku | Typ | Znaczenie |
|---|---|---|
| 0 | u32 | `0x114` |
| 4 | u32 | `0x74` |
| 8 | u32 | Suma rozpakowanych danych |
| 12 | u8 | `1` — sposób pakowania |
| 13 | u32 | Rozmiar rozpakowanych danych |
| 17 | strumień | LZ, okno 1024 B, bity LSB-first |

Suma: dla kolejnych pełnych słów u32 `w`: `x = u ^ w`,
`u = x * ((x & 0xFC) | 3)` modulo 2^32, początkowo `u = 0`.
Końcowe 1–3 bajty nie wchodzą do sumy, zgodnie z kodekiem referencyjnym.

Eksport bez zmian zachowuje oryginalne bajty kontenera. Eksport po zmianach
tworzy strumień literałów: bajt zerowych flag przed każdymi ośmioma bajtami.
To wariant obsługiwany przez kodek referencyjny MP, nie kompresja ZIP/zlib.

## Rozpakowane dane

1. Tekst mapy zakończony NUL i u32.
2. Dwie listy nagłówków: przedmioty i czary. Nagłówek obiektu to
   `{u32 id, u32 kind, u16 a, u16 b}`.
3. Bloki danych obiektów, kolejno dla obu list. Po każdej liście
   `u32 0xFFFFFADF` i jeden bajt.
4. Lista identyfikatorów plecaka.
5. Liczba postaci i rekordy postaci: pięć tekstów, u32, parametry `0x704 B`,
   trzy float32 budowy modelu, cztery listy wyposażenia, tekst roli,
   17 bajtów, tekst prototypu.
6. Zmienne zadań `{tekst NUL, float32}`, zakończone pustym tekstem.
7. Dwie u32; ich XOR daje złoto.

Rodzaje obiektów i rozmiary: czar `0x3002/66 B`, broń `0x3004/68 B`,
zbroja `0x3005/108 B`, podręczny `0x3006/56 B`, łup `0x3007/64 B`,
pojemnik czaru `0x3008/56 B`, zadanie `0x3009/56 B`.

## Rozpoznane pola

Offsety względne względem początku bloku parametrów danej postaci:

| Offset | Typ | Parametr |
|---|---|---|
| +0x04 | f32 | EXP łączne |
| +0x08 | f32 | Rozliczenie / wydane EXP |
| +0x0C / +0x10 | f32 | Siła podstawowa / bieżąca |
| +0x14 / +0x18 | f32 | Zręczność podstawowa / bieżąca |
| +0x1C / +0x20 | f32 | Inteligencja podstawowa / bieżąca |
| +0x24 / +0x28 | f32 | Współczynnik ruchu podstawowy / bieżący |
| +0x2C / +0x30 | f32 | Akcje podstawowe / bieżące |
| +0x34 / +0x38 | f32 | Prędkość biegu / chodu |
| +0x3C / +0x40 | f32 | Prędkość skradania / pełzania |
| +0x54 | f32 | Maks. udźwig |
| +0x60 | u32 | Kod LOCOMOTION |
| +0xB0 / +0xB4 | f32 | Wzrok podstawowy / bieżący |
| +0xB8 / +0xBC | f32 | Noktowizja podstawowa / bieżąca |
| +0xC0 / +0xC4 | f32 | Wykrywanie życia podstawowe / bieżące |
| +0x6C8 | u8 | Kradzież / używanie |
| +0x6CB / +0x6CC | u8 | Walka wręcz / strzelanie |
| +0x6CE / +0x6CF / +0x6D0 | u8 | Magia żywiołów / zmysłów / astralna |
| +0x6D3…+0x6EC | u8 | 26 grup zdolności 0–3 |

Blok trzech float32 po parametrach opisuje budowę modelu. Źródła renderera
opisują trzecią oś jako `scale`. W testowym `10.mp` jej wartość
`0.699999988079071` odpowiada widocznemu suwakowi „Wysokość 70”.
Edytor prezentuje tę oś jako `100 × float32`, a przy zapisie dzieli wartość
suwaka przez 100. To mapowanie zgodne z plikiem testowym; nie wykonano
jeszcze próby zmiany suwaka i ponownego wyświetlenia postaci w grze.
Nie jest to wysokość w centymetrach ani ogólny mnożnik skali całego świata.
Wartość w edytorze może przekraczać 100. Edytor przyjmuje nieujemne liczby,
które po podzieleniu przez 100 mieszczą się w skończonym float32. Przykłady:
150 → 1,50, 300 → 3,00, 1000 → 10,00. Nie wprowadzono osobnego limitu gry.

W `10.mp` EXP ma pola `500` i `113`, a ekran tworzenia postaci pokazuje
`Doświadczenie: 500` i koszt `-113`. Dokumentacja referencyjna opisuje
`+0x08` jako wydane EXP. Program zachowuje oba pola osobno i nie przedstawia
automatycznie wyniku odejmowania jako zastępczej wartości EXP.

## Pozycje w testowym 10.mp

| Pole | Offset w rozpakowanych danych | Wartość |
|---|---|---|
| Nazwa / klan | 0x4DF | `Kamaikashi \| klan` |
| Parametry | 0x51D | blok 0x704 B |
| EXP | 0x521 / 0x525 | 500 / 113 |
| Siła | 0x529 / 0x52D | 35 / 35 |
| Zręczność | 0x531 / 0x535 | 25 / 25 |
| Inteligencja | 0x539 / 0x53D | 15 / 15 |
| Budowa modelu | 0xC21 | ok. 0,85 / 0,68 / 0,70 |
| Wysokość / oś scale | 0xC29 | ok. 0,70 → suwak 70 |
| Złoto XOR | 0xC83 | 500 |

Po zmianie długości nazwy dalsze offsety przesuwają się. Edytor nakłada
zmiany na pozycje oryginału, a następnie od nowa analizuje strukturę eksportu.
Pola nie są wyszukiwane przez samą zgodność liczby, a adresy nie są stałe
dla wszystkich plików.

## Kontrole

Edytor odrzuca nieobsługiwane wersje i rodzaje obiektów, złą sumę, ucięcie,
powtórzone ID, brakujące odwołania oraz nierozpoznane dane na końcu.
Zmiany obejmują tylko wybrane zakresy. Pozostałe bajty, w tym czary,
wskaźniki zachowane w statystykach i wyposażenie, pozostają nienaruszone.
Eksport jest rozpakowywany i ponownie analizowany; wszystkie rozpoznane
wartości są porównywane z zamierzonym wynikiem.

## Parametry istniejących czarów

Zakładka Czary udostępnia dziewięć pól w istniejącym rekordzie czaru
0x3002 (66 B). Ich offsety są liczone od początku danego rekordu:

| Offset | Typ | Pole |
|---|---|---|
| +6 | u32 | Czas trwania |
| +10 | f32 | Moc efektu |
| +14 | f32 | Promień obszaru |
| +18 | f32 | Parametr Speed |
| +22 | f32 | Zasięg |
| +26 | u32 | Liczba celów |
| +34 | f32 | Bazowy koszt many |
| +38 | u32 | Złożoność |
| +62 | u32 | Wymagany poziom magii |

Runy (+50..+57), flagi (+30..+33), cena (+42..+45), ID i prototyp są
zachowywane. Nie są przeliczane z bazy i nie mają tu kontrolek do edycji.
Szczegóły i granice weryfikacji: CZARY_MP.md.

## Pochodzenie

- Kodek i opis formatu: Kyr4l, `ei-universal-mod`, rewizja `810a9019a57d1b3081e39d50444f3339ba0fa56f`.
- [Źródło referencyjne dołączone do projektu](../reference/upstream-mp_file.hpp), GPL-3.0-or-later.
- [Opis formatu MP upstream](https://github.com/Kyr4l/ei-universal-mod/blob/810a9019a57d1b3081e39d50444f3339ba0fa56f/docs/file-formats/mp-format.md).
- [Budowa modelu i oś scale](https://github.com/Kyr4l/ei-universal-mod/blob/810a9019a57d1b3081e39d50444f3339ba0fa56f/docs/file-formats/figure-format.md).
- Pliki testowe `examples/9.mp` i `examples/10.mp`.

Mapowanie dodatkowych pól opisują [ruch](RUCH_MP.md), [czary](CZARY_MP.md)
i [wyposażenie](EKWIPUNEK_MP.md). Zakres testów: [VALIDATION.md](VALIDATION.md).
