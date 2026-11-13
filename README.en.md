# Evil Islands MP Tools

An offline multiplayer character (`.mp`) editor for **Evil Islands**, plus a separate patched `GAME.EXE` enabling PvP and multiplayer console commands.

**[Download MP editor](https://github.com/arasusx-cyber/evil-islands-mp-tools/releases/latest/download/Evil_Islands_MP_Editor_Python.zip)** · **[Download PvP + console EXE](https://github.com/arasusx-cyber/evil-islands-mp-tools/releases/latest/download/Evil_Islands_PvP_kody.zip)** · [Polski](README.md)

## MP editor

- Character name/clan, model height, gold, experience, attributes, skills and abilities.
- Movement parameters and LOCOMOTION: walking / levitation.
- Equipment durability, energy, regeneration, material, weight, damage and armour protection.
- Parameters of existing spells while preserving rune IDs, flags and references.
- Original/edited comparisons, undo and export to a new file.

Requires **Python 3.10+** with Tcl/Tk for the GUI. No pip dependencies. Extract the entire editor archive and launch `URUCHOM.bat`, `Edytor_MP.pyw`, or:

```bash
python editor.py
```

The supported character container is `0x114`, version `0x74`. Original files and existing output files are protected from overwriting. See the [editor guide](docs/EDITOR.md) and [format reference](docs/FORMAT_MP.md).

## Patched GAME.EXE

The separate archive enables PvP damage and multiplayer console commands on the host. Preserve the original EXE before replacing it. This is a specific patched binary; its size and SHA-256 are documented in the [EXE guide](docs/EXE.md).

On the host, open the console with `~` and enter:

```text
thingamabob
give 0 money 10000
give 0 exp 10000
```

Use the `give` examples at the base/map screen, outside a mission. PvP does not award experience for player kills, and players retain their ally classification.

## Development

```bash
python -m unittest discover -s tests -v
```

[Development and packaging](docs/DEVELOPMENT.md) · [Validation scope](docs/VALIDATION.md) · [Sources and licensing](NOTICE.md)

Editor code is GPL-3.0-or-later. The editor's licence does not apply to the game's executable.

## Expanded MP character creator variant

This package includes PvP and multiplayer console commands. New characters can have a height of up to **1000** and get **75 extra points** to distribute among Strength, Dexterity, and Intelligence. Each attribute starts at 25. The total is 150, with a cap of 75 per attribute.

**[Download GAME.EXE with the expanded creator](https://github.com/arasusx-cyber/evil-islands-mp-tools/releases/download/v1.0.0/Evil_Islands_1.06_PvP_Kody_Kreator.zip)**
