# SPDX-License-Identifier: GPL-3.0-or-later
"""Run: python -m unittest discover -s tests -v (no extra packages)."""
from pathlib import Path
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mp_core import Editor, MPError, checksum, pack, parse, unpack


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.source = ROOT / "examples/9.mp"
        self.original = self.source.read_bytes()
        self.e = Editor(self.original, source=self.source)

    def test_original_9_and_lossless_export(self):
        self.assertEqual(hashlib.sha256(self.original).hexdigest(),
                         "3ad7bec3c2824c063fb8d39dc5b9ade87e85d98e5ca89d677871cfc62f6fc9a6")
        self.assertEqual(len(self.original), 1108)
        self.assertEqual(len(self.e.raw), 3507)
        self.assertEqual((self.e.get("gold"), self.e.get("m0.xp"), self.e.get("m0.spent")), (21121, 60502, 891))
        self.assertEqual((len(self.e.model.lists[0]), len(self.e.model.lists[1])), (11, 5))
        self.assertEqual(self.e.export_bytes(), self.original)
        self.assertEqual(unpack(pack(self.e.raw)), self.e.raw)

    def test_combined_edit_and_unknown_byte_preservation(self):
        changes = {"gold": 123456789, "m0.xp": 1000000, "m0.spent": 1234,
                   "m0.strength.base": 45, "m0.strength.current": 45,
                   "m0.skill.melee": 100, "m0.perk.0": 3,
                   "m0.name": "Zażółć | Test", "item.1205.damage": 10000,
                   "item.1205.damage_range": 50, "item.1207.weight": 2.5}
        for key, value in changes.items():
            self.e.set(key, value)
        raw = self.e.edited_raw()
        before, after = 0, 0
        for patch in sorted(self.e.patches.values(), key=lambda p: p.at):
            n = patch.at - before
            self.assertEqual(raw[after:after + n], self.e.raw[before:patch.at])
            before = patch.at + patch.length
            after += n + len(patch.data)
        self.assertEqual(raw[after:], self.e.raw[before:])
        reopened = Editor(self.e.export_bytes())
        for key, value in changes.items():
            self.assertEqual(reopened.get(key), value)
        self.assertEqual(reopened.model.backpack, self.e.model.backpack)
        self.assertEqual(reopened.model.members[0].equipment, self.e.model.members[0].equipment)
        for a, b in zip(self.e.model.lists[1], reopened.model.lists[1]):
            self.assertEqual(self.e.raw[a.detail:a.detail + 66], reopened.raw[b.detail:b.detail + 66])
        self.assertEqual(reopened.export_bytes(), self.e.export_bytes())

    def test_each_supported_field_roundtrips(self):
        for field in self.e.fields:
            with self.subTest(key=field.key):
                e = Editor(self.original)
                old = e.get(field.key)
                if field.type == "text":
                    value = "Test"
                elif field.key == "m0.spent":
                    value = 892
                else:
                    value = 1 if old == 0 else min(field.maximum, old + 1)
                actual = e.set(field.key, value)
                reopened = Editor(e.export_bytes())
                self.assertEqual(reopened.get(field.key), actual)

    def test_revert_and_original_are_immutable(self):
        old = self.e.get("gold")
        self.e.set("gold", 98765)
        self.assertEqual(self.e.get("gold", original=True), old)
        self.assertEqual(self.e.original, self.original)
        self.e.undo("gold")
        self.assertFalse(self.e.patches)
        self.e.set("gold", 12345)
        self.e.set("gold", old)
        self.assertFalse(self.e.patches)
        self.assertEqual(self.e.export_bytes(), self.original)

    def test_no_clobber_original_other_files_links_and_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source = folder / "9.mp"
            source.write_bytes(self.original)
            e = Editor.from_file(source)
            e.set("gold", 99999)
            with self.assertRaises(MPError):
                e.save_copy(source)
            existing = folder / "existing.mp"
            existing.write_bytes(b"keep me")
            with self.assertRaises(MPError):
                e.save_copy(existing)
            self.assertEqual(existing.read_bytes(), b"keep me")
            if hasattr(os, "symlink"):
                try:
                    link = folder / "link.mp"
                    link.symlink_to(source)
                except OSError:
                    pass
                else:
                    with self.assertRaises(MPError):
                        e.save_copy(link)
            try:
                hardlink = folder / "hardlink.mp"
                os.link(source, hardlink)
            except OSError:
                pass
            else:
                with self.assertRaises(MPError):
                    e.save_copy(hardlink)
            result = e.save_copy(folder / "9.edited.mp")
            self.assertEqual(Editor.from_file(result).get("gold"), 99999)
            e.save_copy(folder / "9.original.mp", backup=True)
            self.assertEqual((folder / "9.original.mp").read_bytes(), self.original)
            self.assertEqual(source.read_bytes(), self.original)

    def test_values_and_float32_rounding(self):
        for key, value in [("gold", -1), ("gold", 4294967296), ("gold", 1.5),
                           ("m0.skill.melee", 256), ("m0.perk.0", 4),
                           ("m0.xp", "nan"), ("m0.xp", "inf"), ("m0.xp", ""),
                           ("m0.strength.base", -5), ("m0.name", "😀"),
                           ("m0.name", "x\0y"), ("m0.name", "a" * 101),
                           ("unknown", 2)]:
            with self.subTest(key=key, value=value), self.assertRaises(MPError):
                self.e.set(key, value)
        self.e.set("item.1205.weight", "1,23456789")
        actual = struct.unpack("<f", struct.pack("<f", 1.23456789))[0]
        self.assertEqual(self.e.get("item.1205.weight"), actual)
        self.assertEqual(Editor(self.e.export_bytes()).get("item.1205.weight"), actual)
        for value in (0, 0xFFFFFFFF):
            self.e.set("gold", value)
            self.assertEqual(Editor(self.e.export_bytes()).get("gold"), value)
        self.e.set("m0.spent", 100000)
        with self.assertRaises(MPError):
            self.e.export_bytes()

    def test_corrupt_unsupported_and_truncated_files(self):
        bad_checksum = bytearray(self.original)
        bad_checksum[8] ^= 1
        bad_version = bytearray(self.original)
        bad_version[4] = 0
        bad_magic = bytearray(self.original)
        bad_magic[0] = 0
        raw_trailer = self.e.raw + b"\0"
        malformed = [b"", self.original[:100], bytes(bad_checksum), bytes(bad_version),
                     bytes(bad_magic), pack(raw_trailer), self.original + b"garbage"]
        for blob in malformed:
            with self.subTest(size=len(blob)), self.assertRaises(MPError):
                Editor(blob)
        invalid_kind = bytearray(self.e.raw)
        struct.pack_into("<I", invalid_kind, self.e.model.lists[0][0].header + 4, 0x9999)
        with self.assertRaises(MPError):
            Editor(pack(invalid_kind))
        invalid_reference = bytearray(self.e.raw)
        struct.pack_into("<I", invalid_reference, self.e.model.lists[0][1].detail + 40, 0x12345678)
        with self.assertRaises(MPError):
            Editor(pack(invalid_reference))

    def test_two_members_are_edited_independently(self):
        m = self.e.model.members[0]
        count_at = m.strings[0].at - 4
        end = m.prototype.at + m.prototype.length
        member = self.e.raw[m.strings[0].at:end]
        raw = self.e.raw[:count_at] + struct.pack("<I", 2) + member + member + self.e.raw[end:]
        e = Editor(pack(raw))
        self.assertEqual(len(e.model.members), 2)
        e.set("m1.name", "Druga postać")
        e.set("m1.strength.base", 66)
        reopened = Editor(e.export_bytes())
        self.assertEqual(reopened.get("m0.name"), " ")
        self.assertEqual(reopened.get("m0.strength.base"), 25)
        self.assertEqual(reopened.get("m1.name"), "Druga postać")
        self.assertEqual(reopened.get("m1.strength.base"), 66)
        self.assertEqual(reopened.get("gold"), 21121)

    def test_10_matches_screens_and_height_copy_roundtrips(self):
        source = ROOT / "examples/10.mp"
        e = Editor.from_file(source)
        self.assertEqual(hashlib.sha256(e.original).hexdigest(),
                         "c75dae21638f31242523afc64eb77f7f2d214e9e584c87e5887a5b32e6e37068")
        self.assertEqual(len(e.original), 1063)
        self.assertEqual(len(e.raw), 3211)
        expected = {"m0.name": "Kamaikashi | klan", "gold": 500,
                    "m0.xp": 500, "m0.spent": 113, "m0.strength.base": 35,
                    "m0.strength.current": 35, "m0.dexterity.base": 25,
                    "m0.intelligence.base": 15, "m0.capacity": 420}
        for key, value in expected.items():
            self.assertEqual(e.get(key), value)
        self.assertAlmostEqual(e.get("m0.height"), 70, places=5)
        from mp_core import SKILLS
        for i, (key, _, _) in enumerate(SKILLS, 1):
            self.assertEqual(e.get("m0.skill." + key), i)
        self.assertEqual(e.export_bytes(), source.read_bytes())
        original_body = e.raw[e.model.members[0].body:e.model.members[0].body + 12]
        e.set("m0.height", 90)
        e.set("m0.name", "Kamaikashi | test")
        e.set("gold", 12345)
        e.set("m0.xp", 1000)
        exported = e.export_bytes()
        again = Editor(exported)
        self.assertAlmostEqual(again.get("m0.height"), 90, places=5)
        self.assertEqual(again.get("m0.name"), "Kamaikashi | test")
        self.assertEqual(again.get("gold"), 12345)
        self.assertEqual(again.get("m0.xp"), 1000)
        self.assertEqual(again.get("m0.strength.base"), 35)
        self.assertEqual(again.raw[again.model.members[0].body:again.model.members[0].body + 8], original_body[:8])
        for value in [-1, float("inf"), float("nan")]:
            with self.assertRaises(MPError):
                e.set("m0.height", value)

    def test_height_above_game_slider_and_float32_boundary(self):
        from mp_core import MAX_FLOAT32
        e = Editor.from_file(ROOT / "examples/10.mp")
        original_body = e.raw[e.model.members[0].body:e.model.members[0].body + 8]
        for height in (101, 150, 300, 1000, 10000, MAX_FLOAT32 * 100):
            with self.subTest(height=height):
                expected = struct.pack("<f", height / 100)
                e.set("m0.height", height)
                again = Editor(e.export_bytes())
                body = again.model.members[0].body
                self.assertEqual(again.raw[body + 8:body + 12], expected)
                self.assertEqual(again.raw[body:body + 8], original_body)
                self.assertEqual(again.get("m0.height"), struct.unpack("<f", expected)[0] * 100)
        for value in (-1, MAX_FLOAT32 * 200, "nan", "inf"):
            with self.subTest(invalid=value), self.assertRaises(MPError):
                e.set("m0.height", value)

    def test_movement_mapping_and_two_times_copy_preserve_other_bytes(self):
        from mp_core import MOVEMENT
        for filename in ("9.mp", "10.mp"):
            e = Editor.from_file(ROOT / "examples" / filename)
            stats = e.model.members[0].stats
            expected = [1.0, 1.0, 0.46666669845581055, 0.20000001788139343,
                        0.1600000113248825, 0.12506668269634247]
            for (key, _, off, _), value in zip(MOVEMENT, expected):
                self.assertEqual(e.by_key['m0.move.' + key].at, stats + off)
                self.assertEqual(e.get('m0.move.' + key), value)
            for key in ("run", "walk", "sneak", "crawl"):
                e.set('m0.move.' + key, e.get('m0.move.' + key) * 2)
            changed = e.edited_raw()
            # The four speed floats are contiguous; coefficients, actions, height,
            # name, equipment and every other byte must stay unchanged.
            self.assertEqual(changed[:stats + 0x34], e.raw[:stats + 0x34])
            self.assertEqual(changed[stats + 0x44:], e.raw[stats + 0x44:])
            again = Editor(e.export_bytes())
            for key in ("run", "walk", "sneak", "crawl"):
                self.assertEqual(again.get('m0.move.' + key), e.get('m0.move.' + key))
            for key in ("base", "current"):
                self.assertEqual(again.get('m0.move.' + key), 1)
            self.assertEqual(again.get('m0.actions.current'), 15)
            for key, *_ in MOVEMENT:
                for invalid in (-1, float('inf'), float('nan')):
                    with self.assertRaises(MPError):
                        e.set('m0.move.' + key, invalid)

    def test_locomotion_uint32_roundtrip_without_other_changes(self):
        for filename in ("9.mp", "10.mp"):
            e = Editor.from_file(ROOT / "examples" / filename)
            at = e.model.members[0].stats + 0x60
            self.assertEqual(e.by_key['m0.move.locomotion'].at, at)
            self.assertEqual(e.get('m0.move.locomotion'), 1)
            # The user confirmed 2 = levitation. This test checks storage integrity.
            e.set('m0.move.locomotion', 2)
            raw = e.edited_raw()
            self.assertEqual(raw[:at], e.raw[:at])
            self.assertEqual(raw[at + 4:], e.raw[at + 4:])
            self.assertEqual(Editor(e.export_bytes()).get('m0.move.locomotion'), 2)
            for value in (-1, 0x100000000, 1.5, float('nan')):
                with self.assertRaises(MPError):
                    e.set('m0.move.locomotion', value)

    def test_spell_names_parameters_and_backpack_connection(self):
        database = json.loads((ROOT / 'database.json').read_text(encoding='utf-8'))
        e = Editor.from_file(ROOT / 'examples/10.mp', database=database)
        expected = {'effect': 14, 'range': 15, 'radius': 0, 'duration': 1,
                    'mana': 2, 'targets': 1, 'required': 2, 'speed': 10, 'complexity': 2}
        for key, value in expected.items():
            self.assertEqual(e.get('spell.22.' + key), value)
        self.assertEqual(e.spell_metadata(22)['name'], 'Fire Arrow')
        self.assertEqual(e.spell_metadata(22)['prototype'], 0)
        self.assertEqual(e.spell_metadata(22)['rune_bytes'], bytes([10, 0, 0, 0, 0, 0, 0, 0]))
        self.assertEqual(e.spell_metadata(22)['locations'], ('Plecak · Pojemnik na czar #37',))
        self.assertEqual(database['SpellPrototypes'][1], 'Lightning Arc')
        self.assertEqual(e.spell_metadata(15)['name'], 'Healing')
        self.assertIn('Bez powiązania', e.spell_metadata(15)['locations'][0])
        from editor import spell_information
        self.assertIn('#10', spell_information(e, 22))
        self.assertEqual(e.export_bytes(), e.original)

    def test_spell_edits_preserve_runes_flags_prices_prototypes_and_other_bytes(self):
        from mp_core import SPELL_FIELDS
        for filename in ('9.mp', '10.mp'):
            e = Editor.from_file(ROOT / 'examples' / filename)
            values = {'effect': 1e8, 'range': 1e8, 'radius': 15.5, 'duration': 100000000,
                      'mana': 0, 'targets': 100000000, 'required': 0, 'speed': 40, 'complexity': 1}
            for obj in e.model.lists[1]:
                for key, *_ in SPELL_FIELDS:
                    e.set(f'spell.{obj.id}.{key}', values[key])
            raw = e.edited_raw()
            changed = {at for patch in e.patches.values() for at in range(patch.at, patch.at + patch.length)}
            self.assertTrue(all(before == after for at, (before, after) in enumerate(zip(e.raw, raw)) if at not in changed))
            again = Editor(e.export_bytes())
            self.assertEqual(again.model, e.model)
            for obj in e.model.lists[1]:
                for key, *_ in SPELL_FIELDS:
                    self.assertEqual(again.get(f'spell.{obj.id}.{key}'), e.get(f'spell.{obj.id}.{key}'))
                for offset, length in ((0, 6), (30, 4), (42, 20)):
                    at = obj.detail + offset
                    self.assertEqual(again.raw[at:at + length], e.raw[at:at + length])
                self.assertEqual(again.spell_metadata(obj.id)['rune_bytes'], e.spell_metadata(obj.id)['rune_bytes'])

    def test_two_ready_spells_with_custom_runes_are_independent(self):
        # Synthetic layout: a Lightning Arc container in the spell slots and a
        # Fire Arrow container in the backpack. Custom rune IDs are opaque.
        database = json.loads((ROOT / 'database.json').read_text(encoding='utf-8'))
        base = Editor.from_file(ROOT / 'examples/10.mp', database=database)
        raw = bytearray(base.raw)
        lightning = next(o for o in base.model.lists[1] if o.id == 15)
        struct.pack_into('<H', raw, lightning.header + 10, 1)
        raw[lightning.detail + 4] = 1
        custom = bytes([29, 30, 31, 32, 33, 40, 0, 0])
        raw[lightning.detail + 50:lightning.detail + 58] = custom
        holder = next(o for o in base.model.lists[0] if o.id == 24)
        struct.pack_into('<IHH', raw, holder.header + 4, 0x3008, 0, 1)
        struct.pack_into('<HH', raw, holder.detail + 4, 0, 1)
        struct.pack_into('<I', raw, holder.detail + 40, 15)
        member = base.model.members[0]
        lists = [member.equipment[0], [], member.equipment[2], [24]]
        encoded_lists = b''.join(struct.pack('<I', len(ids)) + b''.join(struct.pack('<I', i) for i in ids) for ids in lists)
        self.assertEqual(len(encoded_lists), member.role.at - member.body - 12)
        raw[member.body + 12:member.role.at] = encoded_lists
        e = Editor(pack(raw), database=database)
        self.assertEqual(e.spell_metadata(15)['name'], 'Lightning Arc')
        self.assertIn('Podręczne czary', e.spell_metadata(15)['locations'][0])
        self.assertIn('Plecak', e.spell_metadata(22)['locations'][0])
        self.assertEqual(e.spell_metadata(15)['rune_bytes'], custom)
        fire_before = e.raw[e.model.lists[1][1].detail:e.model.lists[1][1].detail + 66]
        e.set('spell.15.effect', 1e8)
        e.set('spell.15.range', 9999999)
        e.set('spell.15.mana', 0)
        # Editing a longer character name at the same time must not break offsets.
        e.set('m0.name', 'Zażółć | dłuższa nazwa')
        again = Editor(e.export_bytes(), database=database)
        self.assertEqual(again.get('spell.15.effect'), 1e8)
        self.assertEqual(again.get('spell.15.range'), 9999999)
        self.assertEqual(again.get('spell.15.mana'), 0)
        self.assertEqual(again.spell_metadata(15)['rune_bytes'], custom)
        self.assertEqual(again.raw[e.model.lists[1][1].detail:e.model.lists[1][1].detail + 66], fire_before)
        self.assertEqual(again.spell_metadata(15)['locations'], e.spell_metadata(15)['locations'])

    def test_invalid_spell_values_and_unknown_spell_are_rejected(self):
        e = Editor.from_file(ROOT / 'examples/10.mp')
        for key, value in [('effect', 'nan'), ('effect', 1e100), ('mana', -1),
                           ('duration', 1.5), ('duration', 0x100000000), ('targets', -2),
                           ('required', float('inf')), ('radius', -1), ('complexity', 1.5)]:
            with self.subTest(key=key, value=value), self.assertRaises(MPError):
                e.set('spell.22.' + key, value)
        with self.assertRaises(MPError):
            e.set('spell.9999.effect', 1)
        with self.assertRaises(MPError):
            e.spell_metadata(9999)
        self.assertFalse(e.patches)

    def test_new_armour_channels_regeneration_capacity_preserve_other_bytes(self):
        from mp_core import DAMAGE_CHANNELS
        for filename in ("9.mp", "10.mp"):
            with self.subTest(filename=filename):
                e = Editor.from_file(ROOT / "examples" / filename)
                keys = []
                for obj in e.model.lists[0]:
                    if obj.kind in (0x3004, 0x3005):
                        keys.extend([(f"item.{obj.id}.energy_regen", 0.125),
                                     (f"item.{obj.id}.spell_capacity", 10000)])
                    if obj.kind == 0x3005:
                        for vector in (1, 2):
                            keys.extend((f"item.{obj.id}.protection.{vector}.{key}", vector * 1000 + i)
                                        for i, (key, _) in enumerate(DAMAGE_CHANNELS))
                changed = set()
                for key, value in keys:
                    field = e.by_key[key]
                    changed.update(range(field.at, field.at + field.length))
                    e.set(key, value)
                raw = e.edited_raw()
                self.assertTrue(all(a == b for i, (a, b) in enumerate(zip(e.raw, raw)) if i not in changed))
                reopened = Editor(e.export_bytes())
                for key, value in keys:
                    self.assertEqual(reopened.get(key), value)
                for obj in e.model.lists[1]:
                    self.assertEqual(reopened.raw[obj.detail:obj.detail + 66], e.raw[obj.detail:obj.detail + 66])

    def test_material_changes_both_copies_and_undo_is_complete(self):
        for filename in ("9.mp", "10.mp"):
            e = Editor.from_file(ROOT / "examples" / filename)
            for obj in e.model.lists[0]:
                key = f"item.{obj.id}.material"
                if key not in e.by_key:
                    continue
                with self.subTest(filename=filename, item=obj.id):
                    original = e.get(key)
                    e.set(key, (original + 1) % 33)
                    raw = e.edited_raw()
                    self.assertEqual(struct.unpack_from("<H", raw, obj.header + 8)[0], e.get(key))
                    self.assertEqual(struct.unpack_from("<H", raw, obj.detail + 4)[0], e.get(key))
                    allowed = {obj.header + 8, obj.header + 9, obj.detail + 4, obj.detail + 5}
                    self.assertTrue(all(a == b for i, (a, b) in enumerate(zip(e.raw, raw)) if i not in allowed))
                    reopened = Editor(e.export_bytes())
                    checked = next(o for o in reopened.model.lists[0] if o.id == obj.id)
                    self.assertEqual(checked.a, e.get(key))
                    self.assertEqual(checked.b, obj.b)
                    e.undo(key)
                    self.assertEqual(e.export_bytes(), e.original)
            obj = next(o for o in e.model.lists[0] if o.kind in (0x3004, 0x3005))
            e.set(f"item.{obj.id}.material", 24)
            e.set("m0.name", "Dłuższa nazwa | próba")
            checked = Editor(e.export_bytes())
            self.assertEqual(checked.get(f"item.{obj.id}.material"), 24)
            self.assertEqual(checked.get("m0.name"), "Dłuższa nazwa | próba")

    def test_repair_recharge_use_edited_maxima_and_rollback_on_failure(self):
        e = Editor.from_file(ROOT / "examples/10.mp")
        items = [o for o in e.model.lists[0] if o.kind in (0x3004, 0x3005)]
        for obj in items:
            e.set(f"item.{obj.id}.durability", 1)
            e.set(f"item.{obj.id}.energy", 0)
        damaged = Editor(e.export_bytes())
        damaged.set(f"item.{items[0].id}.max_durability", 1234)
        self.assertEqual(damaged.fill_equipment("durability"), len(items))
        self.assertEqual(damaged.fill_equipment("energy"), len(items))
        self.assertEqual(damaged.fill_equipment("energy"), 0)
        checked = Editor(damaged.export_bytes())
        for obj in items:
            for resource in ("durability", "energy"):
                self.assertEqual(checked.get(f"item.{obj.id}.{resource}"), checked.get(f"item.{obj.id}.max_{resource}"))
        self.assertEqual(checked.get(f"item.{items[0].id}.durability"), 1234)
        raw = bytearray(e.edited_raw())
        struct.pack_into("<f", raw, items[1].detail + 20, float("nan"))
        broken = Editor(pack(raw))
        broken.set("gold", 123)
        previous = broken.patches.copy()
        with self.assertRaises(MPError):
            broken.fill_equipment("energy")
        self.assertEqual(broken.patches, previous)
        with self.assertRaises(MPError):
            broken.fill_equipment("unknown")

    def test_senses_and_extended_item_bounds(self):
        e = Editor.from_file(ROOT / "examples/10.mp")
        offsets = {"sight.base": 0xB0, "infra.base": 0xB8, "infra.current": 0xBC,
                   "detectlife.base": 0xC0, "detectlife.current": 0xC4}
        for key, off in offsets.items():
            self.assertEqual(e.by_key["m0." + key].at, e.model.members[0].stats + off)
            e.set("m0." + key, 77.5)
        checked = Editor(e.export_bytes())
        for key in offsets:
            self.assertEqual(checked.get("m0." + key), 77.5)
        for key, value in [("item.30.material", -1), ("item.30.material", 65536),
                           ("item.30.material", 1.2), ("item.30.energy_regen", "nan"),
                           ("item.30.energy_regen", -1), ("item.30.spell_capacity", 1.5),
                           ("item.2.protection.1.acid", float("inf"))]:
            with self.subTest(key=key, value=value), self.assertRaises(MPError):
                e.set(key, value)
        e.set("item.30.energy_regen", 0)
        self.assertEqual(Editor(e.export_bytes()).get("item.30.energy_regen"), 0)

    def test_material_labels_and_item_description_follow_pending_changes(self):
        from editor import field_number, item_information, load_database
        e = Editor.from_file(ROOT / "examples/10.mp", database=load_database())
        field = e.by_key["item.30.material"]
        self.assertIn("Silicon", field_number(e, field))
        e.set(field.key, 24)
        self.assertIn("Mithrill", field_number(e, field))
        description = item_information(e, 30)
        self.assertIn("19 · Silicon → 24 · Mithrill", description)
        self.assertIn("nie przelicza", description)
        e.set(field.key, 60000)
        self.assertIn("własny / nieznany", field_number(e, field))


if __name__ == "__main__":
    unittest.main()
