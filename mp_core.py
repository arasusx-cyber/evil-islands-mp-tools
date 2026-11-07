"""Local Evil Islands multiplayer character editor; Python 3.10+.

SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2026 Kyr4l (MP codec and format research).
Copyright (C) 2026 MP Editor contributors (Python port and editor).
Adapted from the supplied mp_file.hpp and previous JavaScript editor.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import struct
from typing import Union

MAX_RAW = 16 * 1024 * 1024
MAX_FILE = 20 * 1024 * 1024
MAX_FLOAT32 = struct.unpack("<f", bytes.fromhex("ffff7f7f"))[0]
DETAIL = {0x3002: 66, 0x3004: 68, 0x3005: 108, 0x3006: 56,
          0x3007: 64, 0x3008: 56, 0x3009: 56}
KIND = {0x3002: ("Czar", "SpellPrototypes"), 0x3004: ("Broń", "Weapons"),
        0x3005: ("Zbroja", "Armors"), 0x3006: ("Przedmiot podręczny", "QuickItems"),
        0x3007: ("Łup / materiał", "LootItems"), 0x3008: ("Pojemnik na czar", "QuickItems"),
        0x3009: ("Przedmiot zadania", "QuestItems")}
SKILLS = [("melee", "Walka wręcz", 0x6CB), ("archery", "Strzelanie", 0x6CC),
          ("steal", "Kradzież / używanie", 0x6C8), ("elemental", "Magia żywiołów", 0x6CE),
          ("sensory", "Magia zmysłów", 0x6CF), ("astral", "Magia astralna", 0x6D0)]
PERKS = ["Miecze", "Topory", "Sztylety", "Włócznie", "Broń obuchowa", "Łuki", "Kusze",
         "Ogień", "Błyskawice", "Kwas", "Iluzja", "Wróżbiarstwo", "Zaklinanie", "Leczenie",
         "Dominacja", "Widzenie w nocy", "Życie", "Energia (mana)", "Regeneracja",
         "Odzyskiwanie energii", "Szybkość / akcje", "Udźwig", "Cios w plecy", "Siła",
         "Zręczność", "Inteligencja"]
# SpellAddonInfo.txt, mptrans indexes 9, 10, 13..16 (index * 4 bytes).
# Names are documented; whether a particular game build reloads/recalculates them
# must be checked in that build. These are raw stored values, not labelled m/s.
MOVEMENT = [
    ("base", "Współczynnik ruchu · podstawowy", 0x24, "movecoeff.natural"),
    ("current", "Współczynnik ruchu · bieżący", 0x28, "movecoeff.total"),
    ("run", "Prędkość biegu", 0x34, "runspeed"),
    ("walk", "Prędkość chodu", 0x38, "walkspeed"),
    ("sneak", "Prędkość skradania / przyklęku", 0x3C, "crawlspeed"),
    ("crawl", "Prędkość pełzania leżąc", 0x40, "liespeed"),
]
# Confirmed by the user's BalanceTool observation and test of this MP field.
LOCOMOTION_NAMES = {1: "Chodzenie", 2: "Lewitacja"}
# Two independently serialized armour absorption vectors: seven damage channels.
# CArmor read/write 0x6A3A70/0x6A3AA0, with the common item block first.
DAMAGE_CHANNELS = [("piercing", "Kłute"), ("slashing", "Cięte"),
                   ("bludgeoning", "Obuchowe"), ("fire", "Ogień"),
                   ("acid", "Kwas"), ("lightning", "Błyskawice"),
                   ("general", "Ogólne")]
# Offsets inside a serialized 66-byte CSpell record. Confirmed against
# GAME.EXE CSpell::Write (0x68B920) and the supplied reference spell builder.
SPELL_FIELDS = [
    ("effect", "Moc / siła efektu", 10, "f32", "Znaczenie zależy od czaru: np. obrażenia, leczenie lub siła działania."),
    ("range", "Zasięg", 22, "f32", "Zapisany zasięg czaru w jednostkach gry."),
    ("radius", "Promień obszaru działania", 14, "f32", "Zapisany promień, a nie pole powierzchni. Działanie obszarowe zależy też od typu czaru."),
    ("duration", "Czas trwania · jednostki gry", 6, "u32", "Wartość całkowita z zapisu; nie jest przeliczana na sekundy. Czar natychmiastowy może mieć tu 1."),
    ("mana", "Bazowy koszt many", 34, "f32", "Koszt przed przeliczeniem przez inteligencję i pozostałe zasady gry."),
    ("targets", "Liczba celów", 26, "u32", "Zapisana liczba celów. Sposób wybierania celów zależy od typu czaru i flag."),
    ("required", "Wymagany poziom magii", 62, "u32", "Wymagana umiejętność przy użyciu czaru; nie jest to poziom postaci."),
    ("speed", "Prędkość · parametr Speed", 18, "f32", "Pole Speed prototypu; jego zastosowanie zależy od rodzaju czaru."),
    ("complexity", "Złożoność", 38, "u32", "Wartość złożoności zapisana w czarze. Nie jest to liczba run i nie jest automatycznie przeliczana."),
]


class MPError(ValueError):
    """A rejected file, edit or export."""


def checksum(raw: bytes) -> int:
    result = 0
    for (word,) in struct.iter_unpack("<I", raw[:len(raw) // 4 * 4]):
        x = result ^ word
        result = (x * ((x & 0xFC) | 3)) & 0xFFFFFFFF
    return result


class BitReader:
    def __init__(self, data: bytes):
        self.data, self.pos, self.buf, self.count = data, 17, 0, 0

    def byte(self) -> int:
        if self.pos >= len(self.data):
            raise MPError("Ucięty strumień danych MP.")
        result = self.data[self.pos]
        self.pos += 1
        return result

    def bits(self, n: int) -> int:
        while self.count < n:
            self.buf |= self.byte() << self.count
            self.count += 8
        result = self.buf & ((1 << n) - 1)
        self.buf >>= n
        self.count -= n
        return result

    def length(self) -> int:
        if not self.bits(1):
            return 4 if self.bits(1) else 2
        if not self.bits(1):
            if self.bits(1):
                return self.bits(2) + 7
            return self.bits(3) + 11 if self.bits(1) else 3
        if not self.bits(1):
            return self.bits(6) + 35 if self.bits(1) else 5
        if not self.bits(1):
            return 6
        return self.bits(7) + 99 if self.bits(1) else self.bits(4) + 19

    def offset(self) -> int:
        if self.bits(1):
            return self.bits(10) + 354 if self.bits(1) else self.bits(12) + 1378
        if self.bits(1):
            return self.bits(8) + 98 if self.bits(1) else self.bits(6) + 34
        if self.bits(1):
            if self.bits(1):
                return self.bits(1) if self.bits(1) else self.bits(4) + 18
            return self.bits(2) + 6
        return self.bits(2) + 2 if self.bits(1) else self.bits(3) + 10


def unpack(data: bytes) -> bytes:
    if len(data) < 17:
        raise MPError("Za krótki plik MP.")
    if len(data) > MAX_FILE:
        raise MPError("Plik przekracza limit 20 MiB.")
    head, version, expected = struct.unpack_from("<III", data)
    if head != 0x114:
        raise MPError("To nie jest plik postaci MP (wymagany nagłówek 0x114).")
    if version != 0x74:
        raise MPError("Nieobsługiwana wersja. Wymagana 0x74 / 116.")
    if data[12] != 1:
        raise MPError("Nieobsługiwany sposób pakowania MP.")
    size, = struct.unpack_from("<I", data, 13)
    if not 0 < size <= MAX_RAW:
        raise MPError("Nieprawidłowy rozmiar rozpakowanych danych.")
    reader, raw, window, pos = BitReader(data), bytearray(), bytearray(1024), 0
    while len(raw) < size:
        if not reader.bits(1):
            value = reader.byte()
            raw.append(value)
            window[pos] = value
            pos = (pos + 1) & 1023
        else:
            length, offset = reader.length(), reader.offset()
            if len(raw) + length > size:
                raise MPError("Nieprawidłowa długość fragmentu skompresowanych danych.")
            for _ in range(length):
                value = window[(pos - offset - 1) & 1023]
                raw.append(value)
                window[pos] = value
                pos = (pos + 1) & 1023
    if reader.pos != len(data):
        raise MPError("Dodatkowe nierozpoznane dane za skompresowanym strumieniem.")
    if checksum(raw) != expected:
        raise MPError("Błędna suma kontrolna. Plik jest uszkodzony albo ma inny format.")
    return bytes(raw)


def pack(raw: bytes) -> bytes:
    if not 0 < len(raw) <= MAX_RAW:
        raise MPError("Nieprawidłowy rozmiar danych do zapisu.")
    out = bytearray(struct.pack("<IIIBI", 0x114, 0x74, checksum(raw), 1, len(raw)))
    for offset in range(0, len(raw), 8):
        out.append(0)  # Eight literal flags; accepted by the supplied game codec.
        out.extend(raw[offset:offset + 8])
    return bytes(out)


@dataclass(frozen=True)
class StringRef:
    at: int
    length: int


@dataclass
class ObjectInfo:
    id: int
    kind: int
    a: int
    b: int
    header: int
    detail: int = 0


@dataclass
class Member:
    strings: list[StringRef]
    stats: int
    body: int
    equipment: list[list[int]]
    role: StringRef
    prototype: StringRef


@dataclass
class Model:
    zone: StringRef
    lists: list[list[ObjectInfo]]
    backpack: list[int]
    members: list[Member]
    variables: list[tuple[StringRef, int]]
    money: int


class Reader:
    def __init__(self, raw: bytes):
        self.raw, self.pos = raw, 0

    def take(self, n: int) -> int:
        if n < 0 or self.pos + n > len(self.raw):
            raise MPError("Ucięta struktura zapisu.")
        start = self.pos
        self.pos += n
        return start

    def u32(self) -> int:
        return struct.unpack_from("<I", self.raw, self.take(4))[0]

    def u16(self) -> int:
        return struct.unpack_from("<H", self.raw, self.take(2))[0]

    def string(self) -> StringRef:
        end = self.raw.find(b"\0", self.pos)
        if end < 0:
            raise MPError("Niedomknięty tekst w zapisie.")
        at = self.pos
        self.pos = end + 1
        return StringRef(at, self.pos - at)

    def count(self, maximum: int = 10000) -> int:
        n = self.u32()
        if n > maximum:
            raise MPError("Nieprawidłowa liczba elementów w zapisie.")
        return n

    def ids(self, maximum: int = 10000) -> list[int]:
        return [self.u32() for _ in range(self.count(maximum))]


def parse(raw: bytes) -> Model:
    r = Reader(raw)
    zone = r.string()
    r.take(4)
    lists = []
    for _ in range(2):
        objects = []
        for _ in range(r.count()):
            at = r.pos
            ident, kind, a, b = r.u32(), r.u32(), r.u16(), r.u16()
            if kind not in DETAIL:
                raise MPError(f"Nieobsługiwany rodzaj obiektu: 0x{kind:X}.")
            objects.append(ObjectInfo(ident, kind, a, b, at))
        lists.append(objects)
    ids = set()
    for objects in lists:
        for obj in objects:
            if obj.id in ids:
                raise MPError("Powtórzony identyfikator obiektu.")
            ids.add(obj.id)
            obj.detail = r.take(DETAIL[obj.kind])
            if struct.unpack_from("<I", raw, obj.detail)[0] != obj.id:
                raise MPError(f"Niespójne dane obiektu #{obj.id}.")
        if r.u32() != 0xFFFFFADF:
            raise MPError("Nieprawidłowy koniec listy obiektów.")
        r.take(1)
    backpack, members = r.ids(), []
    for _ in range(r.count(16)):
        strings = [r.string() for _ in range(5)]
        r.take(4)
        stats, body = r.take(0x704), r.take(12)
        equipment = [r.ids(1000) for _ in range(4)]
        role = r.string()
        r.take(17)
        members.append(Member(strings, stats, body, equipment, role, r.string()))
    if not members:
        raise MPError("W pliku nie ma postaci.")
    variables = []
    while True:
        name = r.string()
        if name.length == 1:
            break
        if len(variables) >= 10000:
            raise MPError("Zbyt wiele zmiennych zadań.")
        variables.append((name, r.take(4)))
    money = r.take(8)
    if r.pos != len(raw):
        raise MPError("Dodatkowe nierozpoznane dane na końcu pliku. Zapis zablokowany.")
    refs = backpack + [i for member in members for group in member.equipment for i in group]
    if any(i != 0xFFFFFFFF and i not in ids for i in refs):
        raise MPError("Odwołanie do brakującego przedmiotu.")
    spell_ids = {obj.id for obj in lists[1]}
    for obj in lists[0]:
        if obj.kind in (0x3004, 0x3005, 0x3008):
            spell, = struct.unpack_from("<I", raw, obj.detail + 40)
            if spell != 0xFFFFFFFF and spell not in spell_ids:
                raise MPError(f"Obiekt #{obj.id} odwołuje się do brakującego czaru.")
    return Model(zone, lists, backpack, members, variables, money)


Value = Union[int, float, str]


@dataclass(frozen=True)
class Field:
    key: str
    group: str
    label: str
    at: int
    type: str = "f32"
    length: int = 4
    minimum: float = 0
    maximum: float = 1e9
    hint: str = ""
    mirrors: tuple[int, ...] = ()


@dataclass(frozen=True)
class Patch:
    at: int
    length: int
    data: bytes
    key: str


class Editor:
    def __init__(self, original: bytes, source: Path | str | None = None,
                 encoding: str = "cp1250", database: dict | None = None):
        self.original = bytes(original)
        self.raw = unpack(self.original)
        self.model = parse(self.raw)
        self.source = Path(source).resolve() if source is not None else None
        self.encoding = encoding
        self.database = database or {}
        self.patches: dict[str, Patch] = {}
        self.fields = self._fields()
        self.by_key = {f.key: f for f in self.fields}

    @classmethod
    def from_file(cls, source: Path | str, **kwargs) -> Editor:
        path = Path(source)
        if path.stat().st_size > MAX_FILE:
            raise MPError("Plik jest większy niż 20 MiB.")
        with path.open("rb") as stream:
            data = stream.read(MAX_FILE + 1)
        return cls(data, source=path, **kwargs)

    def decode(self, ref: StringRef) -> str:
        return self.raw[ref.at:ref.at + ref.length - 1].decode(self.encoding, errors="replace")

    def item_name(self, obj: ObjectInfo) -> str:
        names = self.database.get(KIND[obj.kind][1], [])
        return names[obj.b] if obj.b < len(names) else f"Wiersz #{obj.b}"

    def spell_group(self, obj: ObjectInfo) -> str:
        return f"{self.item_name(obj)} · czar #{obj.id} · prototyp #{obj.b}"

    def spell_metadata(self, ident: int) -> dict:
        """Read-only identity, rune bytes and connections; never rebuild custom runes."""
        obj = next((o for o in self.model.lists[1] if o.kind == 0x3002 and o.id == ident), None)
        if obj is None:
            raise MPError(f"Brak czaru #{ident} w zapisie.")
        locations = []
        equipment_names = ("Broń", "Pas", "Zbroja", "Podręczne czary")
        for item in self.model.lists[0]:
            if item.kind not in (0x3004, 0x3005, 0x3008):
                continue
            if struct.unpack_from("<I", self.raw, item.detail + 40)[0] != ident:
                continue
            holders = []
            if item.id in self.model.backpack:
                holders.append("Plecak")
            for member_id, member in enumerate(self.model.members, 1):
                for slot, ids in enumerate(member.equipment):
                    if item.id in ids:
                        holders.append(f"Postać {member_id}: {equipment_names[slot]}")
            where = ", ".join(holders) or "Przedmiot poza wyposażeniem"
            locations.append(f"{where} · {KIND[item.kind][0]} #{item.id}")
        for member_id, member in enumerate(self.model.members, 1):
            if ident in member.equipment[3]:
                locations.append(f"Postać {member_id}: Podręczne czary · bezpośrednie ID")
        if not locations:
            locations.append("Bez powiązania z przedmiotem lub slotem")
        return {"id": obj.id, "prototype": obj.b, "name": self.item_name(obj),
                "locations": tuple(locations),
                "rune_bytes": self.raw[obj.detail + 50:obj.detail + 58],
                "flags": struct.unpack_from("<I", self.raw, obj.detail + 30)[0]}

    def _fields(self) -> list[Field]:
        fields = [Field("gold", "Zasoby", "Złoto", self.model.money, "money", 8,
                        maximum=0xFFFFFFFF, hint="Dwie liczby uint32 połączone XOR.")]
        for index, member in enumerate(self.model.members):
            prefix = f"m{index}."
            group = f"Postać {index + 1}"
            fields.append(Field(prefix + "name", group, "Nazwa / tag klanu", member.strings[0].at,
                                "text", member.strings[0].length, hint="Maks. 100 znaków."))
            fields.append(Field(prefix + "height", group, "Wysokość / skala modelu", member.body + 8,
                                "height", maximum=MAX_FLOAT32 * 100,
                                hint="Można przekroczyć 100. Skala modelu: wartość / 100, zapis float32. "
                                     "Np. 150 → 1,50; 300 → 3,00. Nie są to centymetry."))
            for key, label, off, maximum in [
                ("xp", "Doświadczenie łącznie", 4, 1e12),
                ("spent", "Doświadczenie wydane", 8, 1e12),
                ("strength.base", "Siła · podstawa", 0xC, 1e6),
                ("strength.current", "Siła · bieżąca", 0x10, 1e6),
                ("dexterity.base", "Zręczność · podstawa", 0x14, 1e6),
                ("dexterity.current", "Zręczność · bieżąca", 0x18, 1e6),
                ("intelligence.base", "Inteligencja · podstawa", 0x1C, 1e6),
                ("intelligence.current", "Inteligencja · bieżąca", 0x20, 1e6),
                ("actions.base", "Akcje · podstawa", 0x2C, 1e6),
                ("actions.current", "Akcje · bieżąca", 0x30, 1e6),
                ("capacity", "Maksymalny udźwig", 0x54, 1e9),
                ("sight", "Zasięg wzroku", 0xB4, 100000),
            ]:
                fields.append(Field(prefix + key, group, label, member.stats + off,
                                    maximum=maximum, hint="Gra może przeliczyć wartości bieżące."))
            for key, label, off, source_name in MOVEMENT:
                fields.append(Field(prefix + "move." + key, group + " / Ruch", label,
                                    member.stats + off, maximum=MAX_FLOAT32,
                                    hint=f"{source_name}: wartość zapisana w MP, bez przeliczenia na m/s. "
                                         "Eksperymentalne: gra może ją przeliczyć po wczytaniu. "
                                         "Testuj osobno prędkości i współczynniki ruchu."))
            for key, label, off in [
                ("sight.base", "Zasięg wzroku · podstawa", 0xB0),
                ("infra.base", "Noktowizja · podstawa", 0xB8),
                ("infra.current", "Noktowizja · bieżąca", 0xBC),
                ("detectlife.base", "Wykrywanie życia · podstawa", 0xC0),
                ("detectlife.current", "Wykrywanie życia · bieżące", 0xC4),
            ]:
                fields.append(Field(prefix + key, group + " / Zmysły", label,
                                    member.stats + off, maximum=MAX_FLOAT32,
                                    hint="Wartość z tabeli mptrans. Gra może przeliczać wartość bieżącą z podstawy i efektów."))
            fields.append(Field(prefix + "move.locomotion", group + " / Ruch", "LOCOMOTION · kod trybu ruchu",
                                member.stats + 0x60, "u32", maximum=0xFFFFFFFF,
                                hint="Kod skopiowany z RaceModels do zapisu MP; w 9.mp i 10.mp: 1. "
                                     "Pole potwierdzone analizą GAME.EXE (0x5138AD–0x5138B0). "
                                     "1 = chodzenie; 2 = lewitacja — potwierdzone przez użytkownika. "
                                     "Znaczenie pozostałych kodów nie jest ustalone."))
            for key, label, off in SKILLS:
                fields.append(Field(prefix + "skill." + key, group + " / Umiejętności", label,
                                    member.stats + off, "u8", 1, maximum=255,
                                    hint="Standardowo 0–100; wyższe poziomy zależą od moda."))
            for i, label in enumerate(PERKS):
                fields.append(Field(prefix + f"perk.{i}", group + " / Zdolności", label,
                                    member.stats + 0x6D3 + i, "u8", 1, maximum=3,
                                    hint="0 brak · 1 specjalista · 2 ekspert · 3 mistrz."))
        for obj in self.model.lists[0]:
            group = f"{self.item_name(obj)} [#{obj.id}]"
            prefix = f"item.{obj.id}."
            if obj.kind in (0x3004, 0x3005, 0x3007):
                fields.append(Field(prefix + "material", group, "Materiał · ID", obj.detail + 4,
                                    "u16", 2, maximum=65535, mirrors=(obj.header + 8,),
                                    hint="Zmiana materiału zapisuje ID w obu miejscach pliku. "
                                         "Nie przelicza automatycznie obrażeń, ochrony, energii ani trwałości. "
                                         "Nazwy pochodzą z bazy klasycznej; użyj ID istniejącego w bazie Twojej gry."))
            if obj.kind in (0x3004, 0x3005):
                for key, label, off in [("durability", "Trwałość", 8), ("max_durability", "Maks. trwałość", 12),
                                        ("energy", "Energia", 16), ("max_energy", "Maks. energia", 20),
                                        ("weight", "Waga", 28)]:
                    fields.append(Field(prefix + key, group, label, obj.detail + off))
                fields.append(Field(prefix + "energy_regen", group, "Regeneracja energii przedmiotu · współczynnik",
                                    obj.detail + 24, maximum=MAX_FLOAT32,
                                    hint="Ułamek maksymalnej energii dodawany przy aktualizacji przedmiotu. "
                                         "0,001 = 0,1%; 0,01 = 1%; 1 = 100%. "
                                         "W przekazanym GAME.EXE zero oznacza natychmiastowe uzupełnienie, a nie wyłączenie regeneracji. "
                                         "To energia wyposażenia, nie wigor postaci."))
                fields.append(Field(prefix + "spell_capacity", group, "Pojemność magiczna · Slots", obj.detail + 48,
                                    "u32", 4, maximum=0xFFFFFFFF,
                                    hint="Zapisana pojemność magiczna przedmiotu; nie liczba przycisków ekwipunku. "
                                         "Nie dodaje ani nie przebudowuje osadzonego czaru."))
                if obj.kind == 0x3004:
                    fields.append(Field(prefix + "damage", group, "Obrażenia minimalne", obj.detail + 56))
                    fields.append(Field(prefix + "damage_range", group, "Rozrzut obrażeń", obj.detail + 60,
                                        hint="Maks. obrażenia = minimum + rozrzut."))
                else:
                    for vector, start in [(1, 52), (2, 80)]:
                        for i, (key, label) in enumerate(DAMAGE_CHANNELS):
                            fields.append(Field(prefix + f"protection.{vector}.{key}", group,
                                                f"Ochrona {vector} · {label}", obj.detail + start + 4 * i,
                                                maximum=MAX_FLOAT32,
                                                hint="Wartość pochłaniania w jednym z dwóch zapisanych zestawów ochrony. "
                                                     "Nie jest procentem. Zestawy są edytowane niezależnie; "
                                                     "materiał i pozostałe rodzaje ochrony pozostają bez zmian."))
            elif obj.kind == 0x3007:
                fields.append(Field(prefix + "quantity", group, "Ilość", obj.detail + 48,
                                    "u32", 4, maximum=0xFFFFFFFF))
        for obj in self.model.lists[1]:
            if obj.kind != 0x3002:
                continue
            for key, label, off, typ, hint in SPELL_FIELDS:
                fields.append(Field(f"spell.{obj.id}.{key}", self.spell_group(obj), label,
                                    obj.detail + off, typ,
                                    maximum=MAX_FLOAT32 if typ == "f32" else 0xFFFFFFFF,
                                    hint=hint + " Runy, prototyp i flagi pozostają zachowane."))
        return fields

    def get(self, key: str, original: bool = False) -> Value:
        f = self.by_key[key]
        patch = None if original else self.patches.get(key)
        data = patch.data if patch else self.raw[f.at:f.at + f.length]
        if f.type == "text":
            return data[:-1].decode(self.encoding, errors="replace")
        if f.type == "money":
            a, b = struct.unpack("<II", data)
            return a ^ b
        if f.type == "height":
            return struct.unpack("<f", data)[0] * 100
        return struct.unpack({"f32": "<f", "u32": "<I", "u16": "<H", "u8": "<B"}[f.type], data)[0]

    def set(self, key: str, value: Value) -> Value:
        if key not in self.by_key:
            raise MPError(f"Nieobsługiwane pole: {key}.")
        f = self.by_key[key]
        if f.type == "text":
            value = str(value)
            if "\0" in value or len(value) > 100:
                raise MPError("Nazwa musi mieć najwyżej 100 znaków i nie może zawierać NUL.")
            try:
                data = value.encode(self.encoding) + b"\0"
            except UnicodeEncodeError as exc:
                raise MPError("Nazwa zawiera znaki niedostępne w wybranym kodowaniu.") from exc
        else:
            try:
                # A comma is accepted as a decimal separator; grouping separators are not needed.
                number = float(value.replace(",", ".")) if isinstance(value, str) else float(value)
            except (ValueError, TypeError, OverflowError) as exc:
                raise MPError("Wpisz poprawną liczbę.") from exc
            if not math.isfinite(number):
                raise MPError("Liczba musi być skończona.")
            if not f.minimum <= number <= f.maximum:
                raise MPError(f"Dozwolony zakres: {f.minimum:g}–{f.maximum:g}.")
            if f.type not in ("f32", "height") and not number.is_integer():
                raise MPError("To pole wymaga liczby całkowitej.")
            if f.type == "money":
                a, = struct.unpack_from("<I", self.raw, f.at)
                data = struct.pack("<II", a, a ^ int(number))
            elif f.type in ("f32", "height"):
                try:
                    data = struct.pack("<f", number / 100 if f.type == "height" else number)
                except OverflowError as exc:
                    raise MPError("Liczba przekracza zakres float32.") from exc
                # Bounds apply to the exact rounded value that will enter the game.
                actual, = struct.unpack("<f", data)
                if f.type == "height":
                    actual *= 100
                if not math.isfinite(actual) or not f.minimum <= actual <= f.maximum:
                    raise MPError("Wartość po zaokrągleniu float32 przekracza zakres pola.")
            else:
                data = struct.pack({"u8": "<B", "u16": "<H", "u32": "<I"}[f.type], int(number))
        if data == self.raw[f.at:f.at + f.length]:
            self.patches.pop(key, None)
        else:
            self.patches[key] = Patch(f.at, f.length, data, key)
        return self.get(key)

    def undo(self, key: str):
        self.patches.pop(key, None)

    def fill_equipment(self, resource: str) -> int:
        """Repair or recharge all stored weapons/armour as one reversible operation."""
        if resource not in ("durability", "energy"):
            raise MPError("Wybierz trwałość albo energię wyposażenia.")
        previous = self.patches.copy()
        count = 0
        try:
            for obj in self.model.lists[0]:
                if obj.kind not in (0x3004, 0x3005):
                    continue
                key = f"item.{obj.id}.{resource}"
                maximum = self.get(f"item.{obj.id}.max_{resource}")
                if self.get(key) != maximum:
                    self.set(key, maximum)
                    count += 1
        except (MPError, ValueError, OverflowError):
            self.patches = previous
            raise
        return count

    def validate(self):
        for index, _ in enumerate(self.model.members):
            xp, spent = self.get(f"m{index}.xp"), self.get(f"m{index}.spent")
            # Existing unusual mod values can be inspected but never silently normalized.
            if not math.isfinite(xp) or not math.isfinite(spent) or spent > xp:
                raise MPError(f"Postać {index + 1}: wydane EXP musi być skończone i nie większe od łącznego.")

    def edited_raw(self) -> bytes:
        out, cursor = bytearray(), 0
        patches = list(self.patches.values())
        for key, patch in self.patches.items():
            for at in self.by_key[key].mirrors:
                patches.append(Patch(at, patch.length, patch.data, key))
        for patch in sorted(patches, key=lambda p: p.at):
            if patch.at < cursor or patch.at + patch.length > len(self.raw):
                raise MPError("Nakładające się lub nieprawidłowe zmiany. Eksport zablokowany.")
            out.extend(self.raw[cursor:patch.at])
            out.extend(patch.data)
            cursor = patch.at + patch.length
        out.extend(self.raw[cursor:])
        if len(out) > MAX_RAW:
            raise MPError("Zmodyfikowany zapis przekracza limit rozmiaru.")
        return bytes(out)

    def export_bytes(self) -> bytes:
        self.validate()
        raw = self.edited_raw()
        parse(raw)
        out = pack(raw) if self.patches else self.original
        if unpack(out) != raw:
            raise MPError("Błąd kontroli eksportu. Niczego nie zapisano.")
        # A fresh parser also re-resolves moved offsets following an edited name.
        checked = Editor(out, encoding=self.encoding, database=self.database)
        for f in self.fields:
            if checked.get(f.key) != self.get(f.key):
                # NaNs in opaque, unedited mod fields are kept byte-for-byte.
                a, b = checked.get(f.key), self.get(f.key)
                if not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)):
                    raise MPError(f"Nieudane sprawdzenie pola: {f.label}.")
        return out

    def save_copy(self, target: Path | str, backup: bool = False) -> Path:
        path = Path(target).expanduser()
        if path.suffix.lower() != ".mp":
            raise MPError("Plik wynikowy musi mieć rozszerzenie .mp.")
        if self.source is not None:
            try:
                same = path.resolve() == self.source or (path.exists() and path.samefile(self.source))
            except OSError:
                same = path.resolve() == self.source
            if same:
                raise MPError("Nie można nadpisać oryginału. Wybierz inną nazwę pliku.")
        data = self.original if backup else self.export_bytes()
        # Exclusive creation also protects existing files, symlinks, hardlinks and races.
        created = False
        try:
            with path.open("x+b") as stream:
                created = True
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                # Verify through the same descriptor, without resolving the path again.
                stream.seek(0)
                if stream.read() != data:
                    raise MPError("Weryfikacja pliku po zapisie nie powiodła się.")
        except FileExistsError as exc:
            raise MPError("Plik o tej nazwie już istnieje. Wybierz nową nazwę — niczego nie nadpisano.") from exc
        except Exception:
            if created:
                path.unlink(missing_ok=True)
            raise
        return path.resolve()

